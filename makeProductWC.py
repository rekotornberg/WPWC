import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import ConnectTimeout
import csv

consumer_key = 'consumer_key'
consumer_secret = 'consumer_secret'

def make_api_request_get_article_id(per_page):
    service_url = 'SERCIVE_URL'
    api_key = 'API_KEY'

    url = f"{service_url}?api_key={api_key}"

    payload = {
        "getArticles": {
            "articleCountry": "FI",
            "provider": providerCode,
            "dataSupplierIds": Number,
            "genericArticleIds":Number,
            "lang": "FI",
            "perPage": per_page,
            "includeMisc": True,
            "includeGenericArticles": True,
            "includeReplacesArticles": True,
            "includeArticleCriteria": True,
            "includePDFs": True,
            "includeImages": True,
            "includeArticleStatusFacets": True,
            "includeComparableNumbers": True,
            "includeArticleLogisticsCriteria": True,
            "includeGTINs": True,
            "includeOEMNumbers": True,
            "page": 1
    
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    } 

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        return response.json()
    except ConnectTimeout:
        print("ConnectTimeoutError occurred. Retrying...")
        return make_api_request_get_article_id(per_page)  # Recursive call to retry
    except requests.exceptions.RequestException as e:
        return {"error": f"Error occurred: {str(e)}"}

def create_woocommerce_product(article):
    wc_api_url_products = 'https://yourSite.com/wp-json/wc/v3/products'
    print(wc_api_url_products)

    headers = {'Content-Type': 'application/json'}
    auth = HTTPBasicAuth(consumer_key, consumer_secret)

    article_status_id = article['misc']['articleStatusId']
    if article_status_id in [0, 14]:
        backorders = 'no'
    elif article_status_id in [1, 11]:
        backorders = 'notify'
    else:
        backorders = 'no'
    #'stock_quantity': article['misc']['quantityPerPackage'],
    product_data = {
        'name': article['genericArticles'][0]['genericArticleDescription'],
        'type': 'simple',
        'regular_price': '10.00',  # Placeholder price, real price from another API
        'sku': article['articleNumber'],
        'manage_stock': True,
        
        'backorders': backorders,
        'images': [{'src': image['imageURL800']} for image in article['images']] if article.get('images') else [{'src': 'https://yourSite.com/wp-content/uploads/2024/06/kuvatulossa_kamoka.jpg'}],
        'attributes': generate_attributes(article),
        'short_description': generate_short_description(article),
        'meta_data': [
            {
                'key': '_woodmart_product_custom_tab_title_2',
                'value': 'Vertailunumerot'
            },
            {
                'key': '_woodmart_product_custom_tab_content_type_2',
                'value': 'text'
            },
            {
                'key': '_woodmart_product_custom_tab_content_2',
                'value': generate_oem_numbers_content(article['oemNumbers'])
            },
            {
                'key': '_woodmart_product_custom_tab_title',
                'value': 'Yhteensopivuus'
            },
            {
                'key': '_woodmart_product_custom_tab_content_type',
                'value': 'text'
            },
            {
                'key': '_woodmart_product_custom_tab_content',
                'value': '[nayta_yhteensopivuus]'     
            }
            
        ]
    }

    for generic_article in article['genericArticles']:
        category_id = get_category_id_by_generic_article_id(generic_article['genericArticleId'])
        if category_id:
            product_data.setdefault('categories', []).append({'id': category_id})

    try:
        response = requests.post(wc_api_url_products, headers=headers, auth=auth, json=product_data, timeout=60)
        response.raise_for_status()
    except ConnectTimeout:
        print("ConnectTimeoutError occurred. Retrying...")
        create_woocommerce_product(article)  # Recursive call to retry
    except requests.exceptions.RequestException as e:
        print(f"Error occurred while creating product: {str(e)}")


def generate_oem_numbers_content(oem_numbers):
    content = '<table><thead><tr><th>VALMISTAJA</th><th>NUMERO</th></tr></thead><tbody>'
    for oem in oem_numbers:
        content += f'<tr><td>{oem["mfrName"]}</td><td>{oem["articleNumber"]}<a class="C2cb" href="#" data-copy2clipboard="{oem["articleNumber"]}">&#x1F4CB;</a></td></tr>'
    content += '</tbody></table>'
    return content.strip()

def get_existing_attributes(auth, wc_api_url_attributes):
    try:
        response = requests.get(wc_api_url_attributes, auth=auth, timeout=60)
        response.raise_for_status()
        return response.json()
    except ConnectTimeout:
        print("ConnectTimeoutError occurred while fetching attributes. Retrying...")
        return get_existing_attributes(auth, wc_api_url_attributes)  # Recursive call to retry
    except requests.exceptions.RequestException as e:
        print(f"Error occurred while fetching attributes: {str(e)}")
        return []

def create_attribute(name, auth, wc_api_url_attributes):
    slug = generate_slug(name)
    payload = {
        'name': name,
        'slug': slug,
        'type': 'select'
    }
    try:
        response = requests.post(wc_api_url_attributes, json=payload, auth=auth, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error occurred while creating attribute '{name}': {str(e)}")
        return None

def generate_slug(name):
    slug = name.lower().replace(' ', '-')
    if (len(slug) > 27):
        slug = slug[:27]
    return slug

def generate_attributes(article):
    attributes = []
    auth = HTTPBasicAuth(consumer_key, consumer_secret)
    
    wc_api_url_attributes = 'https://yourSite.com/wp-json/wc/v3/products/attributes'
    existing_attributes = get_existing_attributes(auth, wc_api_url_attributes)

    attribute_map = {}

    for criteria in article.get('articleCriteria', []):
        attribute_name = criteria['criteriaDescription']
        formatted_value = criteria['formattedValue']

        if attribute_name in attribute_map:
            attribute_map[attribute_name]['options'].append(formatted_value)
        else:
            attribute_id = None

            for attr in existing_attributes:
                if attr['name'] == attribute_name:
                    attribute_id = attr['id']
                    break

            if attribute_id is None:
                print(f"Attribute '{attribute_name}' not found in WooCommerce. Creating it...")
                new_attribute = create_attribute(attribute_name, auth, wc_api_url_attributes)
                if new_attribute:
                    attribute_id = new_attribute['id']
                    existing_attributes.append(new_attribute)
                else:
                    continue

            attribute_map[attribute_name] = {
                'id': attribute_id,
                'name': attribute_name,
                'visible': True,
                'options': [formatted_value]
            }

    for attribute in attribute_map.values():
        attributes.append(attribute)

    # Add genericArticleId as an attribute and make it hidden
    generic_article_id = article['genericArticles'][0]['genericArticleId']
    attribute_name = 'Generic Article ID'
    attribute_id = None
    for attr in existing_attributes:
        if attr['name'] == attribute_name:
            attribute_id = attr['id']
            break

    if attribute_id is None:
        print(f"Attribute '{attribute_name}' not found in WooCommerce. Creating it...")
        new_attribute = create_attribute(attribute_name, auth, wc_api_url_attributes)
        if new_attribute:
            attribute_id = new_attribute['id']
            existing_attributes.append(new_attribute)
        else:
            return attributes

    attribute = {
        'id': attribute_id,
        'name': attribute_name,
        'visible': False,  # Make this attribute hidden
        'options': [str(generic_article_id)]
    }
    attributes.append(attribute)

    
    gtins = article.get('gtins', [])
    if gtins:
        ean = gtins[0][:-1]  
        attribute_name = 'EAN'
        attribute_id = None
        for attr in existing_attributes:
            if attr['name'] == attribute_name:
                attribute_id = attr['id']
                break

        if attribute_id is None:
            print(f"Attribute '{attribute_name}' not found in WooCommerce. Creating it...")
            new_attribute = create_attribute(attribute_name, auth, wc_api_url_attributes)
            if new_attribute:
                attribute_id = new_attribute['id']
                existing_attributes.append(new_attribute)
            else:
                return attributes

        attribute = {
            'id': attribute_id,
            'name': attribute_name,
            'visible': True,
            'options': [ean]
        }
        attributes.append(attribute)

    return attributes

def generate_short_description(article):
    short_description = '<table><tbody>'
    attributes = {}
    current_row = []

    for criteria in article.get('articleCriteria', []):
        criteria_description = criteria["criteriaDescription"]
        formatted_value = criteria["formattedValue"]
        if criteria_description in attributes:
            attributes[criteria_description].append(formatted_value)
        else:
            attributes[criteria_description] = [formatted_value]

    for attr, values in attributes.items():
        combined_value = ', '.join(values)
        current_row.append(f'<td class="small-font"><b>{attr}:</b></td>')
        current_row.append(f'<td class="small-font">{combined_value}</td>')

        if (len(current_row) == 4):
            short_description += '<tr>' + ''.join(current_row) + '</tr>'
            current_row = []

    # Add EAN to the short description
    gtins = article.get('gtins', [])
    if gtins:
        ean = gtins[0][:-1]  # Remove the last digit
        current_row.append(f'<td class="small-font"><b>EAN:</b></td>')
        current_row.append(f'<td class="small-font">{ean}</td>')

        if (len(current_row) == 4):
            short_description += '<tr>' + ''.join(current_row) + '</tr>'
            current_row = []

    if current_row:  # Add the last row if there are remaining elements
        short_description += '<tr>' + ''.join(current_row) + '</tr>'

    short_description += '</tbody></table>'
    return short_description.strip()

def read_category_mapping_from_csv(filepath):
    category_mapping = {}
    with open(filepath, mode='r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            generic_article_id = int(row['genericArticleId'])
            category_id = int(row['kategoria_Id'])
            category_mapping[generic_article_id] = category_id
    return category_mapping

def check_existing_products(articles):
    existing_skus = set()
    duplicate_articles = []

    wc_api_url_products = 'https://yourSite.com/wp-json/wc/v3/products'
    auth = HTTPBasicAuth(consumer_key, consumer_secret)

    try:
        response = requests.get(wc_api_url_products, auth=auth, timeout=60)
        response.raise_for_status()
        existing_products = response.json()

        for product in existing_products:
            existing_skus.add(product['sku'])

        for article in articles:
            if article['articleNumber'] in existing_skus:
                duplicate_articles.append(article)

        return duplicate_articles

    except ConnectTimeout:
        print("ConnectTimeoutError occurred while checking existing products. Retrying...")
        return check_existing_products(articles)  # Recursive call to retry
    except requests.exceptions.RequestException as e:
        print(f"Error occurred while checking existing products: {str(e)}")

def get_category_id_by_generic_article_id(generic_article_id):
    if not hasattr(get_category_id_by_generic_article_id, "category_mapping"):
        # Load category mapping if it hasn't been loaded yet
        get_category_id_by_generic_article_id.category_mapping = read_category_mapping_from_csv('csvExample.csv')
    
    return get_category_id_by_generic_article_id.category_mapping.get(generic_article_id)

if __name__ == "__main__":
    response = make_api_request_get_article_id(per_page=1000)
    if 'error' in response:
        print(f"API Request Error: {response['error']}")
    else:
        total_articles = response['totalMatchingArticles']
        articles = response['articles']
        
        duplicate_articles = check_existing_products(articles)

        if duplicate_articles:
            print("Duplicate products already exist:")
            for article in duplicate_articles:
                print(article['mfrName'], article['articleNumber'])
        else:
            for article in articles:
                create_woocommerce_product(article)
            print("Products created successfully.")