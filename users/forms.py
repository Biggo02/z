from django import forms
from django.contrib.auth import authenticate
from .models import User, IdentityVerification


PROFESSION_CHOICES = [
    ('', 'Sélectionnez votre profession'),
    ('AGRICULTEUR', 'Agriculteur / Agricultrice'),
    ('ARTISAN', 'Artisan / Artisane'),
    ('AVOCAT', 'Avocat / Avocate'),
    ('BANQUIER', 'Banquier / Banquière'),
    ('COMPTABLE', 'Comptable'),
    ('COMMERÇANT', 'Commerçant / Commerçante'),
    ('COMMUNICATION', 'Communication / Médias'),
    ('ENSEIGNANT', 'Enseignant / Enseignante'),
    ('ENTREPRENEUR', 'Entrepreneur / Entrepreneuse'),
    ('ETUDIANT', 'Étudiant / Étudiante'),
    ('FONCTIONNAIRE', 'Fonctionnaire'),
    ('INGENIEUR', 'Ingénieur / Ingénieure'),
    ('JURISTE', 'Juriste'),
    ('MEDECIN', 'Médecin'),
    ('MILITAIRE', 'Militaire'),
    ('OUVRIER', 'Ouvrier / Ouvrière'),
    ('PHARMACIEN', 'Pharmacien / Pharmacienne'),
    ('PROFESSION_LIBERALE', 'Profession libérale'),
    ('SANTE', 'Professionnel de santé'),
    ('TECHNICIEN', 'Technicien / Technicienne'),
    ('TRANSPORTEUR', 'Transport / Logistique'),
    ('VENDEUR', 'Vendeur / Vendeuse'),
    ('SANS_EMPLOI', 'Sans emploi'),
    ('RETRAITE', 'Retraité / Retraitée'),
    ('AUTRE', 'Autre'),
]


class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, min_length=10)
    password_confirmation = forms.CharField(widget=forms.PasswordInput, min_length=10)
    profession = forms.ChoiceField(choices=PROFESSION_CHOICES, required=False)

    class Meta:
        model = User
        fields = ['last_name', 'postname', 'first_name', 'email', 'phone', 'birth_date', 'sex', 'profession']
        widgets = {'birth_date': forms.DateInput(attrs={'type': 'date'})}

    def clean_email(self):
        value = self.cleaned_data['email'].lower().strip()
        if User.objects.filter(email__iexact=value).exists():
            raise forms.ValidationError('Cet email est déjà utilisé.')
        return value

    def clean_phone(self):
        value = self.cleaned_data['phone'].strip()
        if User.objects.filter(phone=value).exists():
            raise forms.ValidationError('Ce numéro est déjà utilisé.')
        return value

    def clean(self):
        data = super().clean()
        if data.get('password') != data.get('password_confirmation'):
            raise forms.ValidationError('Les mots de passe ne correspondent pas.')
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = None
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class EmailLoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        data = super().clean()
        if data.get('email') and data.get('password'):
            self.user_cache = authenticate(self.request, username=data['email'].lower().strip(), password=data['password'])
            if self.user_cache is None:
                raise forms.ValidationError('Email ou mot de passe incorrect.')
        return data

    def get_user(self):
        return self.user_cache


class IdentityVerificationForm(forms.ModelForm):
    class Meta:
        model = IdentityVerification
        fields = ['document_type', 'document_file', 'facial_photo']
        widgets = {
            'document_file': forms.ClearableFileInput(attrs={'accept': '.pdf,.jpg,.jpeg,.png'}),
            'facial_photo': forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png,image/webp', 'capture': 'user'}),
        }
        labels = {
            'document_type': 'Type de pièce d’identité',
            'document_file': 'Photo ou scan de la pièce d’identité',
            'facial_photo': 'Photo faciale (selfie)',
        }

    def clean_document_file(self):
        document = self.cleaned_data.get('document_file')
        if document and document.content_type not in {'application/pdf', 'image/jpeg', 'image/png'}:
            raise forms.ValidationError('La pièce doit être un PDF, JPEG ou PNG.')
        return document

    def clean_facial_photo(self):
        photo = self.cleaned_data.get('facial_photo')
        if photo and photo.content_type not in {'image/jpeg', 'image/png', 'image/webp'}:
            raise forms.ValidationError('La photo faciale doit être une image JPEG, PNG ou WebP.')
        return photo
