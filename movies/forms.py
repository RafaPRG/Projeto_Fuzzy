from django import forms


class MovieSearchForm(forms.Form):
    movie_title_pt = forms.CharField(
        label="",
        max_length=120,
        widget=forms.TextInput(
            attrs={
                "class": "form-control search-input",
                "placeholder": "Digite um filme em portugues",
                "autocomplete": "off",
                "spellcheck": "false",
                "required": True,
            }
        ),
    )

    def clean_movie_title_pt(self) -> str:
        value = self.cleaned_data["movie_title_pt"].strip()
        if not value:
            raise forms.ValidationError("Digite o nome de um filme para continuar.")
        return value
