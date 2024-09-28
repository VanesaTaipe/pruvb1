import streamlit as st
import pandas as pd
import re


# Configuración de la página
st.set_page_config(page_title="Chatbot de Restaurante", page_icon="🍽️")
if groq_available:
    from groq import Groq
    try:
        client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    except Exception as e:
        st.error(f"Error initializing Groq client: {e}")
        groq_available = False
# Inicialización del cliente Groq
#client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# Cargar datos
@st.cache_data
def load_data():
    menu_df = pd.read_csv('menu.csv')
    cities_df = pd.read_csv('us-cities.csv')
    return menu_df, cities_df['City'].tolist()

menu_df, delivery_cities = load_data()

# Simplificar el menú
simplified_menu = menu_df[['Category', 'Item', 'Serving Size']]

# Funciones de manejo del menú
def get_menu():
    menu_text = "🍽️ Nuestro Menú:\n\n"
    for category, items in simplified_menu.groupby('Category'):
        menu_text += f"**{category}**\n"
        for _, item in items.head().iterrows():
            menu_text += f"• {item['Item']} - {item['Serving Size']}\n"
        menu_text += "...\n\n"
    menu_text += "Para ver más detalles de una categoría específica, por favor pregúntame sobre ella."
    return menu_text

def get_category_details(category):
    category_items = simplified_menu[simplified_menu['Category'] == category]
    if category_items.empty:
        return f"Lo siento, no encontré información sobre la categoría '{category}'."
    
    details = f"Detalles de {category}:\n\n"
    for _, item in category_items.iterrows():
        details += f"• {item['Item']} - {item['Serving Size']}\n"
    return details

# Funciones de manejo de entregas
def check_delivery(city):
    if city.lower() in [c.lower() for c in delivery_cities]:
        return f"✅ Sí, realizamos entregas en {city}."
    else:
        return f"❌ Lo siento, actualmente no realizamos entregas en {city}."

def get_delivery_cities():
    return "Realizamos entregas en las siguientes ciudades:\n" + "\n".join(delivery_cities[:10]) + "\n..."

# Función de manejo de pedidos
def start_order():
    return ("Para realizar un pedido, por favor sigue estos pasos:\n"
            "1. Revisa nuestro menú\n"
            "2. Dime qué items te gustaría ordenar\n"
            "3. Proporciona tu dirección de entrega\n"
            "4. Confirma tu pedido\n\n"
            "¿Qué te gustaría ordenar?")

# Función de manejo de consultas
def handle_query(query):
    query_lower = query.lower()
    
    if re.search(r'\b(menú|carta)\b', query_lower):
        return get_menu()
    elif re.search(r'\b(entrega|reparto)\b', query_lower):
        city_match = re.search(r'en\s+(\w+)', query_lower)
        if city_match:
            return check_delivery(city_match.group(1))
        else:
            return get_delivery_cities()
    elif re.search(r'\b(pedir|ordenar|pedido)\b', query_lower):
        return start_order()
    elif re.search(r'\b(categoría|categoria)\b', query_lower):
        category_match = re.search(r'(categoría|categoria)\s+(\w+)', query_lower)
        if category_match:
            return get_category_details(category_match.group(2))
    
    # Si no se reconoce la consulta, usamos Groq para generar una respuesta
    messages = st.session_state.messages + [{"role": "user", "content": query}]
    response = client.chat.completions.create(
        messages=[
            {"role": m["role"], "content": m["content"]}
            for m in messages
        ],
        model="mixtral-8x7b-32768",
        max_tokens=150,
        temperature=0.7,
    )
    return response.choices[0].message.content

# Título de la aplicación
st.title("🍽️ Chatbot de Restaurante")

# Inicialización del historial de chat en la sesión de Streamlit
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar mensajes existentes
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Campo de entrada para el usuario
if prompt := st.chat_input("¿En qué puedo ayudarte hoy?"):
    # Agregar mensaje del usuario al historial
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Mostrar el mensaje del usuario
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generar respuesta del chatbot
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = handle_query(prompt)
        message_placeholder.markdown(full_response)
    
    # Agregar respuesta del chatbot al historial
    st.session_state.messages.append({"role": "assistant", "content": full_response})
