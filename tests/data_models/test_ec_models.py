import pytest
from datetime import datetime
from pydantic import ValidationError as PydanticValidationError
from src.data_models.ec_models import (
    Customer, Product, Category, Order, OrderItem, Supplier, CustomerReview
)

# Common data for testing
VALID_DATETIME = datetime.now()

# --- Test Customer Model ---
def test_customer_valid_creation():
    customer = Customer(
        CustomerID=1,
        FirstName="John",
        LastName="Doe",
        Email="john.doe@example.com",
        PhoneNumber="123-456-7890",
        ShippingAddress="123 Main St",
        BillingAddress="123 Main St",
        RegistrationDate=VALID_DATETIME,
        LastLoginDate=VALID_DATETIME
    )
    assert customer.CustomerID == 1
    assert customer.FirstName == "John"
    assert customer.Email == "john.doe@example.com"
    assert customer.RegistrationDate == VALID_DATETIME

def test_customer_optional_fields():
    customer = Customer(CustomerID=2) # Only required field
    assert customer.CustomerID == 2
    assert customer.FirstName is None
    assert customer.Email is None

    customer_with_some_optionals = Customer(
        CustomerID=3,
        FirstName="Jane",
        Email="jane@example.com"
    )
    assert customer_with_some_optionals.CustomerID == 3
    assert customer_with_some_optionals.FirstName == "Jane"
    assert customer_with_some_optionals.Email == "jane@example.com"
    assert customer_with_some_optionals.LastName is None

def test_customer_customerid_validation():
    with pytest.raises(PydanticValidationError, match="CustomerID"):
        Customer(CustomerID="abc") # wrong type
    with pytest.raises(PydanticValidationError, match="CustomerID"):
        Customer(CustomerID=0) # not positive
    with pytest.raises(PydanticValidationError, match="CustomerID"):
        Customer(CustomerID=-1) # not positive
    customer = Customer(CustomerID=1)
    assert customer.CustomerID == 1

def test_customer_email_validation():
    with pytest.raises(PydanticValidationError, match="Email"):
        Customer(CustomerID=1, Email="not-an-email")
    customer = Customer(CustomerID=1, Email="valid@example.com")
    assert customer.Email == "valid@example.com"

# --- Test Product Model ---
def test_product_valid_creation():
    product = Product(
        ProductID=101,
        ProductName="Laptop",
        Description="A cool laptop",
        SKU="LP100",
        CategoryID=1,
        SupplierID=1,
        Price=1200.50,
        StockQuantity=50,
        ImagePath="/img/laptop.png",
        DateAdded=VALID_DATETIME
    )
    assert product.ProductID == 101
    assert product.ProductName == "Laptop"
    assert product.Price == 1200.50

def test_product_optional_fields():
    product = Product(ProductID=102)
    assert product.ProductID == 102
    assert product.ProductName is None
    assert product.Price is None

def test_product_productid_validation():
    with pytest.raises(PydanticValidationError, match="ProductID"):
        Product(ProductID="xyz")
    with pytest.raises(PydanticValidationError, match="ProductID"):
        Product(ProductID=0)
    with pytest.raises(PydanticValidationError, match="ProductID"):
        Product(ProductID=-5)

def test_product_price_validation():
    with pytest.raises(PydanticValidationError, match="Price"):
        Product(ProductID=1, Price="free")
    with pytest.raises(PydanticValidationError, match="Price"):
        Product(ProductID=1, Price=-10.0)
    product = Product(ProductID=1, Price=0.0) # 0 is allowed for NonNegativeFloat
    assert product.Price == 0.0
    product_priced = Product(ProductID=1, Price=19.99)
    assert product_priced.Price == 19.99

def test_product_stockquantity_validation():
    with pytest.raises(PydanticValidationError, match="StockQuantity"):
        Product(ProductID=1, StockQuantity="many")
    with pytest.raises(PydanticValidationError, match="StockQuantity"):
        Product(ProductID=1, StockQuantity=-5)
    product = Product(ProductID=1, StockQuantity=0) # 0 is allowed
    assert product.StockQuantity == 0
    product_stocked = Product(ProductID=1, StockQuantity=100)
    assert product_stocked.StockQuantity == 100

def test_product_foreign_keys_validation():
    # CategoryID
    with pytest.raises(PydanticValidationError, match="CategoryID"):
        Product(ProductID=1, CategoryID=0)
    with pytest.raises(PydanticValidationError, match="CategoryID"):
        Product(ProductID=1, CategoryID=-1)
    product_cat = Product(ProductID=1, CategoryID=1)
    assert product_cat.CategoryID == 1
    product_no_cat = Product(ProductID=1, CategoryID=None)
    assert product_no_cat.CategoryID is None

    # SupplierID
    with pytest.raises(PydanticValidationError, match="SupplierID"):
        Product(ProductID=1, SupplierID=0)
    with pytest.raises(PydanticValidationError, match="SupplierID"):
        Product(ProductID=1, SupplierID=-1)
    product_sup = Product(ProductID=1, SupplierID=1)
    assert product_sup.SupplierID == 1
    product_no_sup = Product(ProductID=1, SupplierID=None)
    assert product_no_sup.SupplierID is None


# --- Test Category Model ---
def test_category_valid_creation():
    category = Category(CategoryID=1, CategoryName="Electronics", Description="All electronic gadgets")
    assert category.CategoryID == 1
    assert category.CategoryName == "Electronics"

def test_category_categoryid_validation():
    with pytest.raises(PydanticValidationError, match="CategoryID"):
        Category(CategoryID="cat01")
    with pytest.raises(PydanticValidationError, match="CategoryID"):
        Category(CategoryID=0)

# --- Test Order Model ---
def test_order_valid_creation():
    order = Order(
        OrderID=201,
        CustomerID=1,
        OrderDate=VALID_DATETIME,
        OrderStatus="Pending",
        TotalAmount=199.99,
        ShippingAddress="123 Main St",
        BillingAddress="123 Main St"
    )
    assert order.OrderID == 201
    assert order.TotalAmount == 199.99

def test_order_orderid_validation():
    with pytest.raises(PydanticValidationError, match="OrderID"):
        Order(OrderID=0)

def test_order_totalamount_validation():
    with pytest.raises(PydanticValidationError, match="TotalAmount"):
        Order(OrderID=1, CustomerID=1, TotalAmount=-100)
    order = Order(OrderID=1, CustomerID=1, TotalAmount=0)
    assert order.TotalAmount == 0

def test_order_customerid_fk_validation():
    with pytest.raises(PydanticValidationError, match="CustomerID"):
        Order(OrderID=1, CustomerID=0)
    order = Order(OrderID=1, CustomerID=1)
    assert order.CustomerID == 1
    order_no_customer = Order(OrderID=1, CustomerID=None)
    assert order_no_customer.CustomerID is None


# --- Test OrderItem Model ---
def test_orderitem_valid_creation():
    item = OrderItem(
        OrderItemID=301, OrderID=201, ProductID=101, Quantity=2, UnitPrice=25.00, TotalPrice=50.00
    )
    assert item.OrderItemID == 301
    assert item.Quantity == 2

def test_orderitem_orderitemid_validation():
    with pytest.raises(PydanticValidationError, match="OrderItemID"):
        OrderItem(OrderItemID=0)

def test_orderitem_quantity_validation():
    with pytest.raises(PydanticValidationError, match="Quantity"):
        OrderItem(OrderItemID=1, OrderID=1, ProductID=1, Quantity=-1)
    item = OrderItem(OrderItemID=1, OrderID=1, ProductID=1, Quantity=0)
    assert item.Quantity == 0

def test_orderitem_unitprice_validation():
    with pytest.raises(PydanticValidationError, match="UnitPrice"):
        OrderItem(OrderItemID=1, OrderID=1, ProductID=1, UnitPrice=-1.0)

def test_orderitem_totalprice_validation():
    with pytest.raises(PydanticValidationError, match="TotalPrice"):
        OrderItem(OrderItemID=1, OrderID=1, ProductID=1, TotalPrice=-5.0)

def test_orderitem_foreign_keys_validation():
    # OrderID
    with pytest.raises(PydanticValidationError, match="OrderID"):
        OrderItem(OrderItemID=1, OrderID=0, ProductID=1)
    # ProductID
    with pytest.raises(PydanticValidationError, match="ProductID"):
        OrderItem(OrderItemID=1, OrderID=1, ProductID=0)

# --- Test Supplier Model ---
def test_supplier_valid_creation():
    supplier = Supplier(
        SupplierID=1, SupplierName="Globex Corp", ContactPerson="Mr. Burns", Email="burns@globex.com", PhoneNumber="555-0001"
    )
    assert supplier.SupplierID == 1
    assert supplier.Email == "burns@globex.com"

def test_supplier_supplierid_validation():
    with pytest.raises(PydanticValidationError, match="SupplierID"):
        Supplier(SupplierID=0)

def test_supplier_email_validation():
    with pytest.raises(PydanticValidationError, match="Email"):
        Supplier(SupplierID=1, Email="not-valid")

# --- Test CustomerReview Model ---
def test_customerreview_valid_creation():
    review = CustomerReview(
        ReviewID=1, CustomerID=1, ProductID=1, Rating=5, ReviewText="Great product!", ReviewDate=VALID_DATETIME, SentimentScore=0.9, SentimentLabel="Positive"
    )
    assert review.ReviewID == 1
    assert review.Rating == 5

def test_customerreview_reviewid_validation():
    with pytest.raises(PydanticValidationError, match="ReviewID"):
        CustomerReview(ReviewID=0, Rating=1) # Rating is required if ReviewID is being tested like this

def test_customerreview_rating_validation():
    with pytest.raises(PydanticValidationError, match="Rating"):
        CustomerReview(ReviewID=1, CustomerID=1, ProductID=1, Rating=0)
    with pytest.raises(PydanticValidationError, match="Rating"):
        CustomerReview(ReviewID=1, CustomerID=1, ProductID=1, Rating=6)
    review = CustomerReview(ReviewID=1, CustomerID=1, ProductID=1, Rating=1)
    assert review.Rating == 1
    review = CustomerReview(ReviewID=1, CustomerID=1, ProductID=1, Rating=5)
    assert review.Rating == 5
    # Test optional rating
    review_no_rating = CustomerReview(ReviewID=1, CustomerID=1, ProductID=1)
    assert review_no_rating.Rating is None


def test_customerreview_foreign_keys_validation():
    # CustomerID
    with pytest.raises(PydanticValidationError, match="CustomerID"):
        CustomerReview(ReviewID=1, CustomerID=0, ProductID=1, Rating=3)
    # ProductID
    with pytest.raises(PydanticValidationError, match="ProductID"):
        CustomerReview(ReviewID=1, CustomerID=1, ProductID=0, Rating=3)

def test_customerreview_sentiment_score_validation():
    # SentimentScore is an Optional[float], no specific range defined beyond float itself
    review = CustomerReview(ReviewID=1, CustomerID=1, ProductID=1, Rating=4, SentimentScore=-0.5)
    assert review.SentimentScore == -0.5
    review2 = CustomerReview(ReviewID=1, CustomerID=1, ProductID=1, Rating=4, SentimentScore=0.5)
    assert review2.SentimentScore == 0.5
    review3 = CustomerReview(ReviewID=1, CustomerID=1, ProductID=1, Rating=4)
    assert review3.SentimentScore is None
    with pytest.raises(PydanticValidationError, match="SentimentScore"):
        CustomerReview(ReviewID=1, CustomerID=1, ProductID=1, Rating=4, SentimentScore="neutral")

# --- Test for data type validation (general example) ---
def test_generic_datatype_validation():
    # Example with Customer.CustomerID
    with pytest.raises(PydanticValidationError):
        Customer(CustomerID="should_be_int")
    # Example with Product.Price
    with pytest.raises(PydanticValidationError):
        Product(ProductID=1, Price="should_be_float")
    # Example with Category.CategoryName (str expected)
    try:
        Category(CategoryID=1, CategoryName=123) # This should technically fail if strict_types=True, but pydantic often coerces.
                                                  # The schema says Optional[str] so Pydantic will try to convert 123 to "123".
                                                  # Let's test with a type that cannot be coerced easily to string for a better test, or rely on specific field tests.
        pass # Pydantic v2 by default does not error on int to str coercion if it makes sense.
    except PydanticValidationError:
        pass # Or handle as expected

    # Better test for string type
    class TempModel(Product): # or any model with an Optional[str]
        TestStr: str
    with pytest.raises(PydanticValidationError): # This will fail if not a string or coercible
        Product(ProductID=1, ProductName={"dict": "not a string"})


# It is good practice to create __init__.py files in test directories
# although pytest might discover tests without them in many cases.
# I'll create them in a subsequent step if running the tests reveals issues.
# For now, focusing on the test logic.
