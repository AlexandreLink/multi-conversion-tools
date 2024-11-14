import streamlit as st
import random

st.title("Accueil - Outils de Conversion Multi-Usage")

# Liste d'URLs de GIFs
gif_urls = [
    "https://media1.tenor.com/m/tez45MQYFYgAAAAd/rickroll-bailu.gif",
    "https://media1.tenor.com/m/1QhTGovPVzUAAAAd/sonfys-shrek.gif",
    "https://media1.tenor.com/m/OoVbm9PgjHwAAAAd/at-your-service-pirates-of-the-carribean.gif",
    "https://media1.tenor.com/m/wKAX9NS_mywAAAAd/donkey-help-you.gif",
    "https://media1.tenor.com/m/QNGf0Ni59BAAAAAd/seth-mc-farland-so-what-can-i-do-for-you.gif",
    "https://media1.tenor.com/m/wfQoupcZhF0AAAAd/hi-hello-there.gif",
    "https://media1.tenor.com/m/cmYNlN-e2GsAAAAd/michael-scott.gif",
    "https://media1.tenor.com/m/rMcQZup4q0gAAAAd/dog-puppy.gif",
    "https://media1.tenor.com/m/0y8taPBtkxIAAAAd/lost-smile.gif",
    "https://media1.tenor.com/m/TytKdgDpA4kAAAAd/truffleshuffle.gif",
    "https://media1.tenor.com/m/sLnbxLK4MDAAAAAd/lost-jin.gif",
    "https://media1.tenor.com/m/6us3et_6HDoAAAAd/hello-there-hi-there.gif",
    "https://media1.tenor.com/m/q8iHGRuR3a8AAAAd/to-the-right-tyga.gif"
]

# Sélectionner un GIF aléatoire
selected_gif = random.choice(gif_urls)

# Afficher le GIF aléatoire
st.image(selected_gif, height=300)  # Ajustez la largeur selon vos préférences

st.write("Bienvenue ! Veuillez sélectionner un outil pour commencer. Ils sont dans la side bar a gauche !")
