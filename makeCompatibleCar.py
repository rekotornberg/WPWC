import csv
import requests
from requests.exceptions import ConnectTimeout

# API-tiedot
consumer_key = 'consumer_key'
consumer_secret = 'consumer_secret'
wc_api_url = 'https://yourSite/wp-json/wc/v3'

def make_api_request(url, payload):
    api_key = 'API_KEY'
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=240)
        response.raise_for_status()
        return response.json()
    except ConnectTimeout:
        print("ConnectTimeoutError occurred. Retrying...")
        return make_api_request(url, payload)  # Recursive call to retry
    except requests.exceptions.RequestException as e:
        print(f"Error occurred: {str(e)}")
        return None

def make_api_request_get_article_id(article_number):
    service_url = 'service_url'
    url = f"{service_url}?api_key=APIKEY"

    payload = {
        "getArticleDirectSearchAllNumbersWithState": {
            "articleCountry": "FI",
            "articleNumber": article_number,
            "lang": "FI",
            "numberType": 0,
            "provider": provider_number,
            "searchExact": True
        }
    }

    return make_api_request(url, payload)

def make_api_request_get_linking_target_ids(article_id):
    service_url = 'service_url'
    url = f"{service_url}?api_key=APIKEY"

    payload = {
        "getArticleLinkedAllLinkingTarget3": {
            "articleCountry": "FI",
            "articleId": article_id,
            "lang": "FI",
            "linkingTargetType": "V, P",
            "provider": provider_number,
            "withMainArticles": True
        }
    }

    return make_api_request(url, payload)

def hae_tuotteen_id_sku(sku):
    url = f"{wc_api_url}/products"
    params = {
        'sku': sku
    }
    response = requests.get(url, auth=(consumer_key, consumer_secret), params=params)
    if response.status_code == 200:
        products = response.json()
        if products:
            return products[0]['id']
        else:
            print(f"Tuotetta ei löytynyt annetulla SKU:lla: {sku}")
            return None
    else:
        print("Virhe tuotteen hakemisessa:", response.text)
        return None

def hae_attribuutin_term_id(nimi):
    url = f"{wc_api_url}/products/attributes"
    response = requests.get(url, auth=(consumer_key, consumer_secret))
    if response.status_code == 200:
        attributes = response.json()
        for attribute in attributes:
            if attribute['name'] == nimi:
                return attribute['id']
              
        print(f"Attribuuttia '{nimi}' ei löytynyt.")
        return None
    else:
        print("Virhe attribuuttien hakemisessa:", response.text)
        return None

def lisaa_attribuutit_tuotteeseen(product_id, attribute_id, attribute_values):
    url = f"{wc_api_url}/products/{product_id}"
    headers = {
        'Content-Type': 'application/json',
    }

    response = requests.get(url, auth=(consumer_key, consumer_secret))
    if response.status_code == 200:
        product_data = response.json()
        current_attributes = product_data.get('attributes', [])
        
        existing_attribute_index = None
        for idx, attr in enumerate(current_attributes):
            if attr['id'] == attribute_id:
                existing_attribute_index = idx
                break

        if existing_attribute_index is not None:
            current_attributes[existing_attribute_index]['options'] = attribute_values
        else:
            current_attributes.append({
                'id': attribute_id,
                'options': attribute_values
            })

        data = {
            'attributes': current_attributes
        }
        response = requests.put(url, headers=headers, auth=(consumer_key, consumer_secret), json=data)
        if response.status_code == 200:
            print(f"{product_id} tuote ID päivitetty")
        else:
            print("Virhe attribuuttien päivittämisessä tuotteeseen:", response.text)
    else:
        print("Virhe tuotetietojen hakemisessa:", response.text)


def process_skus_from_file(filename):
    with open(filename, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            sku = row['SKU']
            article_number = sku
            article_id_response = make_api_request_get_article_id(article_number)
            if article_id_response:
                article_id = article_id_response.get('data', {}).get('array', [{}])[0].get('articleId')
                if article_id:
                    linking_target_ids_response = make_api_request_get_linking_target_ids(article_id)
                    if linking_target_ids_response:
                        try:
                            article_linkages = linking_target_ids_response['data']['array'][0]['articleLinkages']
                            if article_linkages:
                                linking_target_ids = [
                                    item['linkingTargetId']
                                    for linkage in linking_target_ids_response['data']['array']
                                    for item in linkage['articleLinkages']['array']
                                ]
                                if linking_target_ids:
                                    attribute_values = [str(i) for i in linking_target_ids]
                                    product_id = hae_tuotteen_id_sku(sku)
                                    if product_id:
                                        attribute_name = 'Yhteensopivuus_ID'
                                        attribute_id = hae_attribuutin_term_id(attribute_name)
                                        if attribute_id:
                                            lisaa_attribuutit_tuotteeseen(product_id, attribute_id, attribute_values)
                            else:
                                print(f"Ajoneuvoja ei löytynyt SKU:lle {sku}")
                        except KeyError:
                            print("articleLinkages not found in the response")
                    else:
                        print(f"Autoja ei löytynyt SKU:lle {sku}")
                else:
                    print(f"articleId not found for articleNumber: {article_number}")
            else:
                print(f"Tuotetta ei löytynyt SKU:lla {sku}.")

# Käsittele SKU:t tiedostosta
process_skus_from_file('Tuote kategoriat\linkitys-sku.csv')
