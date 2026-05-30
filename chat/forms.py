from django import forms

from .models import Channel, DirectMessage, Message, VoiceChannel


class ChannelForm(forms.ModelForm):
    class Meta:
        model = Channel
        fields = ["name", "description"]


class VoiceChannelForm(forms.ModelForm):
    class Meta:
        model = VoiceChannel
        fields = ["name", "description"]


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ["content", "image", "audio"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 2}),
            "image": forms.ClearableFileInput(attrs={
                "accept": "image/*",
                "class": "visually-hidden",
            }),
            "audio": forms.ClearableFileInput(attrs={
                "accept": "audio/*,.mp3,.wav,.m4a,.ogg,.webm",
                "class": "visually-hidden",
            }),
        }


class DirectMessageForm(forms.ModelForm):
    class Meta:
        model = DirectMessage
        fields = ["content", "image", "audio"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 2}),
            "image": forms.ClearableFileInput(attrs={
                "accept": "image/*",
                "class": "visually-hidden",
            }),
            "audio": forms.ClearableFileInput(attrs={
                "accept": "audio/*,.mp3,.wav,.m4a,.ogg,.webm",
                "class": "visually-hidden",
            }),
        }


class SearchForm(forms.Form):
    q = forms.CharField(label="Search", max_length=100)
