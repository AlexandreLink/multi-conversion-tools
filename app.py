import streamlit as st
import random

st.title("Accueil - Outils de Conversion Multi-Usage")

# Liste d'URLs de GIFs
gif_urls = [
    "https://tenor.com/fr/view/rickroll-bailu-gif-13109126276794815880",
    "https://tenor.com/fr/view/sonfys-shrek-gif-15350610703372212021",
    "https://tenor.com/fr/view/at-your-service-pirates-of-the-carribean-johnny-depp-gif-12788009",
    "https://tenor.com/fr/view/donkey-help-you-how-can-i-help-ya-gif-13880120391864654636",
    "https://tenor.com/fr/view/seth-mc-farland-so-what-can-i-do-for-you-orville-sarcasm-gif-12154903",
    "https://tenor.com/fr/view/hi-hello-there-hello-sup-swag-gif-17652416",
    "https://tenor.com/fr/view/michael-scott-wassup-wassupmybrotha-michaelscott-gif-22017221",
    "https://tenor.com/fr/view/dog-puppy-cute-puppy-puppy-dance-adorable-gif-12449937729095510856",
    "https://tenor.com/fr/view/lost-smile-john-locke-gif-15217431594641756946",
    "https://tenor.com/fr/view/truffleshuffle-gif-4570445",
    "https://tenor.com/fr/view/lost-jin-thumbs-up-gif-26707920",
    "https://tenor.com/fr/view/hello-there-hi-there-greetings-gif-9442662",
    "https://tenor.com/fr/view/to-the-right-tyga-krabby-step-song-follow-my-lead-move-to-my-right-gif-19169357"
]

# Sélectionner un GIF aléatoire
selected_gif = random.choice(gif_urls)

# Afficher le GIF aléatoire
st.image(selected_gif, use_column_width=True)

st.write("Bienvenue ! Veuillez sélectionner un outil pour commencer.")
