from django.shortcuts import render
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
from datetime import datetime


def get_content_selenium(product, clicks=1):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("user-agent=Mozilla/5.0...")

    driver = webdriver.Chrome(options=options)

    try:
        driver.get(f'https://www.alkosto.com/search?text={product}')

        # Esperar carga inicial
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "li.ais-InfiniteHits-item"))
        )

        # Lógica para clicks
        click_count = 0
        while True:
            if clicks is not None and click_count >= clicks:
                break

            try:
                boton = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR,
                                                "button.ais-InfiniteHits-loadMore.button-primary__outline.product__listing__load-more"))
                )
                driver.execute_script("arguments[0].click();", boton)
                click_count += 1
                print(f"Click #{click_count} en 'Mostrar más' exitoso")
                time.sleep(3)
            except Exception as e:
                print(f"Fin de los productos (clicks realizados: {click_count})")
                break

        return driver.page_source, click_count  # Devolvemos HTML y total de clicks

    finally:
        driver.quit()


def home(request):
    product_info_list = []
    product_counter = 0
    start_time = datetime.now()  # Marcamos inicio

    if 'product' in request.GET:
        product = request.GET.get('product')
        print(f"\n🔍 Iniciando scraping para: {product}")

        # Obtener HTML y clicks
        html_content, total_clicks = get_content_selenium(product, clicks=1)

        # Parsear
        soup = BeautifulSoup(html_content, 'html.parser')
        product_items = soup.find_all('li',
                                      class_='ais-InfiniteHits-item product__item js-product-item js-algolia-product-click')

        for item in product_items:
            name_tag = item.find('h3', class_=['product__item__top__title', 'js-algolia-product-click',
                                               'js-algolia-product-title'])
            stars_tag = item.find('span', class_='averageNumber')  # Rating
            old_price_tag = item.find('p', class_='product__price--discounts__old')  # Precio tachado
            discount_price_tag = item.find('span', class_='price')  # Precio actual
            img_c_div = item.find('div', class_='product__item__information__image js-algolia-product-click')
            image_tag = img_c_div.find('img') if img_c_div else None

            # Extraer características técnicas
            specs_container = item.find('ul', class_='product__item__information__key-features--list js-key-list')

            # Inicializar valores por defecto
            storage = "Not specified"
            processor = "Not specified"
            ram = "Not specified"
            screen_size = "Not specified"

            if specs_container:
                spec_items = specs_container.find_all('li', class_='item')
                for spec in spec_items:
                    key = spec.find('div', class_='item--key').get_text(strip=True) if spec.find('div',
                                                                                                class_='item--key') else None
                    value = spec.find('div', class_='item--value').get_text(strip=True) if spec.find('div',
                                                                                                    class_='item--value') else None

                    if key and value:
                        if 'Capacidad de Disco' in key:
                            storage = value
                        elif 'Procesador' in key:
                            processor = value
                        elif 'Memoria RAM' in key:
                            ram = value
                        elif 'Tamaño Pantalla' in key:
                            screen_size = value

            if name_tag and discount_price_tag and image_tag and stars_tag and old_price_tag:
                product_counter += 1
                product_info = {
                    'id': product_counter,
                    'name': name_tag.get_text(strip=True),
                    'stars': stars_tag.get_text(strip=True) if stars_tag else "Sin calificación",
                    'old_price': old_price_tag.get_text(strip=True) if old_price_tag else "Sin descuento",
                    'discount_price': discount_price_tag.get_text(strip=True),
                    'image_url': f"https://www.alkosto.com{image_tag['src']}" if image_tag['src'].startswith('/') else
                    image_tag['src'],
                    'storage': storage,
                    'processor': processor,
                    'ram': ram,
                    'screen_size': screen_size
                }
                product_info_list.append(product_info)

        # Calculamos métricas
        execution_time = (datetime.now() - start_time).total_seconds()

        print("\n" + "═" * 40)
        print(f"Clicks realizados: {total_clicks}")
        print(f"Productos obtenidos: {product_counter}")
        print(f"Tiempo total: {execution_time:.2f} segundos")
        print("═" * 40 + "\n")

    return render(request, 'core/home.html', {'product_info_list': product_info_list})