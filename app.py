import streamlit as st
import pandas as pd
import re
from groq import Groq

# Configuración de la página
st.set_page_config(page_title="Chatbot de Restaurante", page_icon="🍽️")

# Inicialización del cliente Groq
groq_available = True
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error(f"Error initializing Groq client: {e}")
    groq_available = False

# Cargar datos
@st.cache_data
def load_data():
    menu_df = pd.read_csv('menu.csv')
    cities_df = pd.read_csv('us-cities.csv')
    return menu_df, cities_df['City'].tolist()

menu_df, delivery_cities = load_data()

# Simplificar el menú
simplified_menu = menu_df[['Category', 'Item', 'Serving Size', 'Price']]

# Funciones de manejo del menú
def get_menu():
    menu_text = "🍽️ Nuestro Menú:\n\n"
    for category, items in simplified_menu.groupby('Category'):
        menu_text += f"**{category}**\n"
        for _, item in items.iterrows():
            menu_text += f"• {item['Item']} - {item['Serving Size']} - ${item['Price']:.2f}\n"
        menu_text += "\n"
    menu_text += "Para ver más detalles de una categoría específica, por favor pregúntame sobre ella."
    return menu_text

def get_category_details(category):
    category_items = simplified_menu[simplified_menu['Category'] == category]
    if category_items.empty:
        return f"Lo siento, no encontré información sobre la categoría '{category}'."
    
    details = f"Detalles de {category}:\n\n"
    for _, item in category_items.iterrows():
        details += f"• {item['Item']} - {item['Serving Size']} - ${item['Price']:.2f}\n"
    return details

# Funciones de manejo de entregas
def check_delivery(city):
    if city.lower() in [c.lower() for c in delivery_cities]:
        return f"✅ Sí, realizamos entregas en {city}."
    else:
        return f"❌ Lo siento, actualmente no realizamos entregas en {city}."

def get_delivery_cities():
    return "Realizamos entregas en las siguientes ciudades:\n" + "\n".join(delivery_cities[:10]) + "\n..."

# Funciones de manejo de pedidos
def add_to_order(item, quantity):
    if item in st.session_state.current_order:
        st.session_state.current_order[item] += quantity
    else:
        st.session_state.current_order[item] = quantity
    return f"Se ha añadido {quantity} {item}(s) a tu pedido."

def remove_from_order(item):
    if item in st.session_state.current_order:
        del st.session_state.current_order[item]
        return f"Se ha eliminado {item} de tu pedido."
    else:
        return f"{item} no estaba en tu pedido."

def calculate_total():
    total = sum(menu_df.loc[menu_df['Item'] == item, 'Price'].iloc[0] * quantity 
                for item, quantity in st.session_state.current_order.items())
    return total

def start_order():
    return ("Para realizar un pedido, por favor sigue estos pasos:\n"
            "1. Revisa nuestro menú\n"
            "2. Dime qué items te gustaría ordenar\n"
            "3. Proporciona tu dirección de entrega\n"
            "4. Confirma tu pedido\n\n"
            "¿Qué te gustaría ordenar?")

def confirm_order():
    if not st.session_state.current_order:
        return "No hay ningún pedido para confirmar. ¿Quieres empezar uno nuevo?"
    
    order_df = pd.DataFrame(list(st.session_state.current_order.items()), columns=['Item', 'Quantity'])
    order_df['Total'] = order_df.apply(lambda row: menu_df.loc[menu_df['Item'] == row['Item'], 'Price'].iloc[0] * row['Quantity'], axis=1)
    order_df.to_csv('orders.csv', mode='a', header=False, index=False)
    total = calculate_total()
    st.session_state.current_order = {}
    return f"¡Gracias por tu pedido! Ha sido confirmado y guardado. El total es ${total:.2f}"

def cancel_order():
    if not st.session_state.current_order:
        return "No hay ningún pedido para cancelar."
    st.session_state.current_order = {}
    return "Tu pedido ha sido cancelado."

# Función de filtrado de contenido
def is_inappropriate(text):
    inappropriate_words = ['palabrota1', 'palabrota2', 'insulto1', 'insulto2']
    return any(word in text.lower() for word in inappropriate_words)

# Función de manejo de consultas
def handle_query(query):
    if is_inappropriate(query):
        return "Por favor, mantén un lenguaje respetuoso."
    
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
    elif re.search(r'\b(precio|costo)\b', query_lower):
        item_match = re.search(r'(precio|costo)\s+de\s+(.+)', query_lower)
        if item_match:
            item = item_match.group(2)
            price = menu_df.loc[menu_df['Item'].str.lower() == item.lower(), 'Price']
            if not price.empty:
                return f"El precio de {item} es ${price.iloc[0]:.2f}"
            else:
                return f"Lo siento, no encontré el precio de {item}."
    
    # Si no se reconoce la consulta, usamos Groq para generar una respuesta
    if groq_available:
        messages = st.session_state.messages + [{"role": "user", "content": query}]
        try:
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
        except Exception as e:
            st.error(f"Error generating response with Groq: {e}")
            return "Lo siento, no pude entender tu consulta. ¿Podrías reformularla?"
    else:
        return "Lo siento, no pude entender tu consulta. ¿Podrías reformularla?"

# Título de la aplicación
st.title("🍽️ Chatbot de Restaurante")

# Inicialización del historial de chat y pedido actual en la sesión de Streamlit
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_order" not in st.session_state:
    st.session_state.current_order = {}

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
        if "añadir" in prompt.lower() or "agregar" in prompt.lower():
            item_match = re.search(r'(añadir|agregar)\s+(\d+)\s+(.+)', prompt.lower())
            if item_match:
                quantity = int(item_match.group(2))
                item = item_match.group(3)
                full_response = add_to_order(item, quantity)
            else:
                full_response = "No pude entender qué quieres añadir. Por favor, especifica la cantidad y el item."
        elif "eliminar" in prompt.lower() or "quitar" in prompt.lower():
            item_match = re.search(r'(eliminar|quitar)\s+(.+)', prompt.lower())
            if item_match:
                item = item_match.group(2)
                full_response = remove_from_order(item)
            else:
                full_response = "No pude entender qué quieres eliminar. Por favor, especifica el item."
        elif "cancelar" in prompt.lower():
            full_response = cancel_order()
        elif "confirmar" in prompt.lower():
            full_response = confirm_order()
        elif "total" in prompt.lower():
            total = calculate_total()
            full_response = f"El total actual de tu pedido es ${total:.2f}"
        else:
            full_response = handle_query(prompt)
        
        message_placeholder.markdown(full_response)
    
    # Agregar respuesta del chatbot al historial
    st.session_state.messages.append({"role": "assistant", "content": full_response})
