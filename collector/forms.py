from django import forms
from user.models import User
from .models import CollectorProfile

class CollectorUserForm(forms.ModelForm):
    confirm_password = forms.CharField(widget=forms.PasswordInput())

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'password']
        widgets = {
            'password': forms.PasswordInput(),
        }

    # This function runs automatically when the form is created (like constructor)
    def __init__(self, *args, **kwargs):
        # Call Django's default form setup
        super().__init__(*args, **kwargs)
        
        # Check if we are creating a new user (no primary key = new)
        if not self.instance or not self.instance.pk:
            # It's a new user, so password and confirm_password must be filled
            self.fields['password'].required = True
            self.fields['confirm_password'].required = True
        

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data


class CollectorProfileForm(forms.ModelForm):
    class Meta:
        model = CollectorProfile
        fields = ['district', 'official_address', 'tenure_start','profile_picture']
