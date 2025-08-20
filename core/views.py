from django.shortcuts import render
from selenium import webdriver
from selenium.common import TimeoutException
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

        # Esperar carga inicial con manejo de timeout
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "li.ais-InfiniteHits-item"))
            )
        except TimeoutException:
            print(f"Timeout: No se encontraron productos para '{product}'")
            return None, 0, "No se encontraron productos o la página no cargó correctamente"

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

        return driver.page_source, click_count, None  # HTML, clicks, error

    except Exception as e:
        error_msg = f"Error durante el scraping: {str(e)}"
        print(error_msg)
        return None, 0, error_msg
    finally:
        driver.quit()


def home(request):
    product_info_list = []
    error_message = None

    if 'product' in request.GET:
        product = request.GET.get('product')
        print(f"\n🔍 Iniciando scraping para: {product}")

        # Obtener HTML, clicks y posible error
        html_content, total_clicks, error = get_content_selenium(product, clicks=3)

        if error:
            error_message = error
        elif html_content is None:
            error_message = "No se pudo obtener el contenido de la página"
        else:
            # Parsear
            soup = BeautifulSoup(html_content, 'html.parser')
            product_items = soup.find_all('li',
                                          class_='ais-InfiniteHits-item product__item js-product-item js-algolia-product-click')

            for item in product_items:
                name_tag = item.find('h3', class_=['product__item__top__title', 'js-algolia-product-click',
                                                   'js-algolia-product-title'])

                link_tag = item.find('a', class_='product__item__top__link')
                product_url = None

                brand_tag = item.find('div', class_='product__item__information__brand')
                brand = brand_tag.get_text(strip=True) if brand_tag else "Sin marca"

                # Extraer descuento
                discount_percent_tag = item.find('span', class_='label-offer')
                discount_percent = discount_percent_tag.get_text(strip=True) if discount_percent_tag else "Sin descuento"

                if link_tag and link_tag.get('href'):
                    href = link_tag['href']
                    # Asegurar que tenga el dominio
                    if href.startswith('/'):
                        product_url = f"https://www.alkosto.com{href}"
                    else:
                        product_url = href

                stars_tag = item.find('span', class_='averageNumber')
                old_price_tag = item.find('p', class_='product__price--discounts__old')
                discount_price_tag = item.find('span', class_='price')
                img_c_div = item.find('div', class_='product__item__information__image js-algolia-product-click')
                image_tag = img_c_div.find('img') if img_c_div else None

                # Extraer características técnicas
                specs_container = item.find('ul', class_='product__item__information__key-features--list js-key-list')
                specifications = {}

                if specs_container:
                    spec_items = specs_container.find_all('li', class_='item')
                    for spec in spec_items:
                        key = spec.find('div', class_='item--key').get_text(strip=True) if spec.find('div',
                                                                                                     class_='item--key') else None
                        value = spec.find('div', class_='item--value').get_text(strip=True) if spec.find('div',
                                                                                                         class_='item--value') else None

                        if key and value:
                            specifications[key] = value

                if name_tag and discount_price_tag and image_tag:
                    product_info = {
                        'name': name_tag.get_text(strip=True),
                        'brand': brand,
                        'url': product_url,
                        'discount_percent' : discount_percent,
                        'stars': stars_tag.get_text(strip=True) if stars_tag else "Sin calificación",
                        'old_price': old_price_tag.get_text(strip=True) if old_price_tag else "Sin descuento",
                        'discount_price': discount_price_tag.get_text(strip=True),
                        'image_url': f"https://www.alkosto.com{image_tag['src']}" if image_tag and image_tag.get('src',
                                                                                                                 '').startswith(
                            '/') else
                        image_tag['src'] if image_tag else "",
                        'specifications': specifications
                    }
                    product_info_list.append(product_info)

        # Solo para debugging en consola
        print("\n" + "═" * 40)
        print(f"Productos obtenidos: {len(product_info_list)}")
        if error_message:
            print(f"Error: {error_message}")
        print("═" * 40 + "\n")

    return render(request, 'core/home.html', {
        'product_info_list': product_info_list,
        'error_message': error_message
    })
