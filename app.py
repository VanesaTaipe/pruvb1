import streamlit as st
import csv
import json
from datetime import datetime
import os
import re

# Configuración de la página
st.set_page_config(page_title="Chatbot de Restaurante", page_icon="🍽️", layout="wide")

# Inicialización de variables de estado
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'menu' not in st.session_state:
    st.session_state.menu = {}
if 'delivery_cities' not in st.session_state:
    st.session_state.delivery_cities = []
if 'current_order' not in st.session_state:
    st.session_state.current_order = []
if 'initialized' not in st.session_state:
    st.session_state.initialized = False

def load_data():
    """Carga los datos del menú y las ciudades de entrega."""
    try:
        # Cargar el menú
        with open('menu.csv', 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            headers = next(reader)  # Leer los encabezados
            for row in reader:
                category = row[0]
                item = row[1]
                serving_size = row[2]
                if category not in st.session_state.menu:
                    st.session_state.menu[category] = []
                st.session_state.menu[category].append({
                    'Item': item,
                    'Serving Size': serving_size
                })

        # Cargar las ciudades de entrega
        with open('us-cities.csv', 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)  # Saltar la primera línea
            for row in reader:
                if len(row) >= 2:
                    st.session_state.delivery_cities.append(f"{row[0]}, {row[1]}")

        st.session_state.initialized = True
        return True
    except FileNotFoundError:
        st.error("Error: Archivos de datos no encontrados.")
        return False
    except Exception as e:
        st.error(f"Error al cargar los datos: {e}")
        return False

def get_menu(category=None):
    """Devuelve el menú del restaurante de manera organizada."""
    if not st.session_state.menu:
        return "Lo siento, el menú no está disponible en este momento. ¿Puedo ayudarte con algo más?"
    
    if category and category in st.session_state.menu:
        menu_text = f"🍽️ Aquí tienes nuestro menú de {category}:\n\n"
        for item in st.session_state.menu[category]:
            menu_text += f"• {item['Item']} - {item['Serving Size']}\n"
        menu_text += "\n¿Te gustaría ordenar algo de esta categoría?"
    else:
        menu_text = "🍽️ Con gusto te muestro nuestro menú:\n\n"
        for category, items in st.session_state.menu.items():
            menu_text += f"**{category}**\n"
            for item in items[:5]:
                menu_text += f"• {item['Item']} - {item['Serving Size']}\n"
            if len(items) > 5:
                menu_text += "...\n"
            menu_text += "\n"
        menu_text += "¿Te interesa alguna categoría en particular? Puedo darte más detalles si lo deseas."
    return menu_text

def get_delivery_info(city=None):
    """Verifica si se realiza entrega en una ciudad específica o muestra información general."""
    if not city:
        sample_cities = st.session_state.delivery_cities[:5]
        return f"¡Claro! Realizamos entregas en muchas ciudades. Algunos ejemplos son: {', '.join(sample_cities)}... y muchas más. ¿En qué ciudad te encuentras? Puedo verificar si hacemos entregas allí."
    
    city = city.title()  # Capitaliza la primera letra de cada palabra
    for delivery_city in st.session_state.delivery_cities:
        if city in delivery_city:
            return f"¡Buenas noticias! Sí realizamos entregas en {delivery_city}. ¿Te gustaría hacer un pedido?"
    return f"Lo siento, parece que no realizamos entregas en {city} por el momento. ¿Quieres que te muestre algunas ciudades cercanas donde sí entregamos?"

def add_to_order(item, quantity):
    """Añade un ítem al pedido actual."""
    for category in st.session_state.menu.values():
        for menu_item in category:
            if menu_item['Item'].lower() == item.lower():
                st.session_state.current_order.append({
                    'item': menu_item['Item'],
                    'quantity': quantity,
                    'serving_size': menu_item['Serving Size']
                })
                return f"¡Perfecto! He añadido {quantity} x {menu_item['Item']} ({menu_item['Serving Size']}) a tu pedido. ¿Deseas agregar algo más?"
    return f"Lo siento, no pude encontrar '{item}' en nuestro menú. ¿Quieres que te muestre las opciones disponibles?"

def finalize_order():
    """Finaliza el pedido actual y lo registra."""
    if not st.session_state.current_order:
        return "Parece que aún no has agregado nada a tu pedido. ¿Te gustaría ver el menú para empezar?"
    
    order_summary = "Aquí tienes el resumen de tu pedido:\n"
    for item in st.session_state.current_order:
        order_summary += f"• {item['quantity']} x {item['item']} ({item['serving_size']})\n"
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    order_details = {
        'timestamp': timestamp,
        'items': st.session_state.current_order
    }
    
    # Registrar el pedido en un archivo JSON
    if not os.path.exists('orders.json'):
        with open('orders.json', 'w') as f:
            json.dump([], f)
    
    with open('orders.json', 'r+') as f:
        orders = json.load(f)
        orders.append(order_details)
        f.seek(0)
        json.dump(orders, f, indent=4)
    
    st.session_state.current_order = []
    return f"{order_summary}\n¡Genial! Tu pedido ha sido registrado con éxito a las {timestamp}. ¡Gracias por tu compra! ¿Hay algo más en lo que pueda ayudarte?"

def get_bot_response(query):
    """Procesa la consulta del usuario y devuelve una respuesta."""
    query_lower = query.lower()
    
    if "menú" in query_lower or "carta" in query_lower:
        return get_menu()
    elif any(category.lower() in query_lower for category in st.session_state.menu.keys()):
        for category in st.session_state.menu.keys():
            if category.lower() in query_lower:
                return get_menu(category)
    elif "entrega" in query_lower or "reparto" in query_lower:
        for city in st.session_state.delivery_cities:
            if city.split(',')[0].lower() in query_lower:
                return get_delivery_info(city.split(',')[0])
        return get_delivery_info()
    elif "pedir" in query_lower or "ordenar" in query_lower:
        items = re.findall(r'(\d+)\s*x\s*(.+?)(?=\d+\s*x|\s*y\s*|\s*,|$)', query_lower)
        if items:
            responses = []
            for quantity, item in items:
                responses.append(add_to_order(item.strip(), int(quantity)))
            return "\n".join(responses)
        else:
            return "Entiendo que quieres hacer un pedido. ¿Podrías especificar qué te gustaría ordenar? Por ejemplo, puedes decir '2 x hamburguesa' o preguntarme por el menú si necesitas más información."
    elif "finalizar pedido" in query_lower:
        return finalize_order()
    elif "horario" in query_lower:
        return "🕒 Con gusto te comparto nuestro horario:\nLunes a Viernes: 11:00 AM - 10:00 PM\nSábados y Domingos: 10:00 AM - 11:00 PM\n¿Te gustaría hacer una reserva o un pedido?"
    elif "especial" in query_lower:
        return "🌟 ¡Tenemos un especial delicioso hoy! Es una Hamburguesa gourmet con papas fritas. ¿Te gustaría probarlo?"
    else:
        return "Disculpa, no estoy seguro de entender tu pregunta. ¿Puedo ayudarte con información sobre nuestro menú, entregas, realizar un pedido o nuestro horario? No dudes en preguntar sobre cualquiera de estos temas."

def main():
    st.title("🍽️ Chatbot de Restaurante")
    
    if not st.session_state.initialized:
        load_data()
    
    st.write("¡Bienvenido a nuestro restaurante virtual! Estoy aquí para ayudarte con cualquier pregunta sobre nuestro menú, entregas, o para tomar tu pedido. ¿En qué puedo asistirte hoy?")
    
    # Mostrar mensajes anteriores
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Área de entrada del usuario
    if prompt := st.chat_input("Escribe tu mensaje aquí:"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = get_bot_response(prompt)
            message_placeholder.markdown(full_response)
        
        st.session_state.messages.append({"role": "assistant", "content": full_response})

if __name__ == "__main__":
    main()
