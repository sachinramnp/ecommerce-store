from django import template

register = template.Library()

# Real product photography from Pexels. These are remote images so the demo
# products always show photographic product/lifestyle images instead of the
# old illustrated placeholders. User-uploaded images still work as fallback.
PRODUCT_IMAGE_URLS = {
    'Wireless Headphones': 'https://images.pexels.com/photos/3394651/pexels-photo-3394651.jpeg?auto=compress&cs=tinysrgb&w=900',
    'Bluetooth Speaker': 'https://images.pexels.com/photos/5511714/pexels-photo-5511714.jpeg?auto=compress&cs=tinysrgb&w=900',
    'USB-C Fast Charger': 'https://images.pexels.com/photos/28739307/pexels-photo-28739307.jpeg?auto=compress&cs=tinysrgb&w=900',
    'Smart LED Bulb': 'https://images.pexels.com/photos/7140253/pexels-photo-7140253.jpeg?auto=compress&cs=tinysrgb&w=900',
    'Cotton Hoodie': 'https://images.pexels.com/photos/16324397/pexels-photo-16324397.jpeg?auto=compress&cs=tinysrgb&w=900',
    'Classic Denim Jacket': 'https://images.pexels.com/photos/16428589/pexels-photo-16428589.jpeg?auto=compress&cs=tinysrgb&w=900',
    'Programming in Python': 'https://images.pexels.com/photos/1181671/pexels-photo-1181671.jpeg?auto=compress&cs=tinysrgb&w=900',
    'Database Systems Guide': 'https://images.pexels.com/photos/5503752/pexels-photo-5503752.jpeg?auto=compress&cs=tinysrgb&w=900',
    'Algorithm Practice Book': 'https://images.pexels.com/photos/14548367/pexels-photo-14548367.jpeg?auto=compress&cs=tinysrgb&w=900',
    'Laptop Sleeve 15-inch': 'https://images.pexels.com/photos/28086428/pexels-photo-28086428.jpeg?auto=compress&cs=tinysrgb&w=900',
    'Backpack Pro': 'https://images.pexels.com/photos/8249067/pexels-photo-8249067.jpeg?auto=compress&cs=tinysrgb&w=900',
    'Metal Water Bottle': 'https://images.pexels.com/photos/4000090/pexels-photo-4000090.jpeg?auto=compress&cs=tinysrgb&w=900',
    'Desk Lamp': 'https://images.pexels.com/photos/1112598/pexels-photo-1112598.jpeg?auto=compress&cs=tinysrgb&w=900',
    'Non-stick Pan': 'https://images.pexels.com/photos/8680488/pexels-photo-8680488.jpeg?auto=compress&cs=tinysrgb&w=900',
    'Storage Organizer Set': 'https://images.pexels.com/photos/16599976/pexels-photo-16599976.jpeg?auto=compress&cs=tinysrgb&w=900',
}


@register.filter
def product_image_url(product_name):
    return PRODUCT_IMAGE_URLS.get(str(product_name), '')
