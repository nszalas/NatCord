from django import forms

from .models import UserReport


class UserReportForm(forms.ModelForm):
    class Meta:
        model = UserReport
        fields = ["reason"]


class UserReportStatusForm(forms.ModelForm):
    class Meta:
        model = UserReport
        fields = ["status"]
