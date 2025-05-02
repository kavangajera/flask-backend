import datetime

def generate_serial_numbers(product_id, num_products):
    """
    Generate serial numbers for products based on the format:
    dateandtime + productid + productindex
    
    Args:
        product_id (str): The product identifier
        num_products (int): Number of serial numbers to generate
    
    Returns:
        list: A list of serial numbers
    """
    # Get current date and time
    current_datetime = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Initialize empty list to store serial numbers
    serial_numbers = []
    
    # Generate serial numbers
    for i in range(1, num_products + 1):
        serial_number = f"{current_datetime}{"  "}{product_id}{"  "}{i:04d}"
        serial_numbers.append(serial_number)
    
    return serial_numbers

# Basic testing
if __name__ == "__main__":
    # Test case 1: Generate 5 serial numbers for product ID "ABC123"
    test_product_id = "ABC123"
    test_num_products = 5
    
    print(f"Generating {test_num_products} serial numbers for product '{test_product_id}':")
    serial_numbers = generate_serial_numbers(test_product_id, test_num_products)
    
    for i, sn in enumerate(serial_numbers, 1):
        print(f"Serial #{i}: {sn}")
    
    # Test case 2: Generate 3 serial numbers for product ID "XYZ789"
    test_product_id_2 = "XYZ789"
    test_num_products_2 = 3
    
    print(f"\nGenerating {test_num_products_2} serial numbers for product '{test_product_id_2}':")
    serial_numbers_2 = generate_serial_numbers(test_product_id_2, test_num_products_2)
    
    for i, sn in enumerate(serial_numbers_2, 1):
        print(f"Serial #{i}: {sn}")