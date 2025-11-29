from django import forms
from .models import Employee


class EmployeeSelfServiceForm(forms.ModelForm):
    class Meta:
        model = Employee
        # allow employees to update a small safe set of fields
        fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'photo']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.strip()
        return email
