from django import forms

from apps.servers.models import Server


class ServerCreateForm(forms.ModelForm):
    class Meta:
        model = Server
        fields = ["name", "hostname", "public_ip"]

    def clean_name(self):
        return self.cleaned_data["name"].strip()
