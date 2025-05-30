from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, PositiveInt, NonNegativeInt, NonNegativeFloat

class Customer(BaseModel):
    CustomerID: PositiveInt = Field(..., alias='CustomerID')
    FirstName: Optional[str] = Field(None, alias='FirstName')
    LastName: Optional[str] = Field(None, alias='LastName')
    Email: Optional[EmailStr] = Field(None, alias='Email')
    PhoneNumber: Optional[str] = Field(None, alias='PhoneNumber')
    ShippingAddress: Optional[str] = Field(None, alias='ShippingAddress')
    BillingAddress: Optional[str] = Field(None, alias='BillingAddress')
    RegistrationDate: Optional[datetime] = Field(None, alias='RegistrationDate')
    LastLoginDate: Optional[datetime] = Field(None, alias='LastLoginDate')

class Product(BaseModel):
    ProductID: PositiveInt = Field(..., alias='ProductID')
    ProductName: Optional[str] = Field(None, alias='ProductName')
    Description: Optional[str] = Field(None, alias='Description')
    SKU: Optional[str] = Field(None, alias='SKU')
    CategoryID: Optional[PositiveInt] = Field(None, alias='CategoryID')
    SupplierID: Optional[PositiveInt] = Field(None, alias='SupplierID')
    Price: Optional[NonNegativeFloat] = Field(None, alias='Price')
    StockQuantity: Optional[NonNegativeInt] = Field(None, alias='StockQuantity')
    ImagePath: Optional[str] = Field(None, alias='ImagePath')
    DateAdded: Optional[datetime] = Field(None, alias='DateAdded')

class Category(BaseModel):
    CategoryID: PositiveInt = Field(..., alias='CategoryID')
    CategoryName: Optional[str] = Field(None, alias='CategoryName')
    Description: Optional[str] = Field(None, alias='Description')

class Order(BaseModel):
    OrderID: PositiveInt = Field(..., alias='OrderID')
    CustomerID: Optional[PositiveInt] = Field(None, alias='CustomerID')
    OrderDate: Optional[datetime] = Field(None, alias='OrderDate')
    OrderStatus: Optional[str] = Field(None, alias='OrderStatus') # E.g., Pending, Shipped
    TotalAmount: Optional[NonNegativeFloat] = Field(None, alias='TotalAmount')
    ShippingAddress: Optional[str] = Field(None, alias='ShippingAddress') # At the time of order
    BillingAddress: Optional[str] = Field(None, alias='BillingAddress') # At the time of order

class OrderItem(BaseModel):
    OrderItemID: PositiveInt = Field(..., alias='OrderItemID')
    OrderID: Optional[PositiveInt] = Field(None, alias='OrderID')
    ProductID: Optional[PositiveInt] = Field(None, alias='ProductID')
    Quantity: Optional[NonNegativeInt] = Field(None, alias='Quantity')
    UnitPrice: Optional[NonNegativeFloat] = Field(None, alias='UnitPrice') # At the time of order
    TotalPrice: Optional[NonNegativeFloat] = Field(None, alias='TotalPrice')

class Supplier(BaseModel):
    SupplierID: PositiveInt = Field(..., alias='SupplierID')
    SupplierName: Optional[str] = Field(None, alias='SupplierName')
    ContactPerson: Optional[str] = Field(None, alias='ContactPerson')
    Email: Optional[EmailStr] = Field(None, alias='Email')
    PhoneNumber: Optional[str] = Field(None, alias='PhoneNumber')

class CustomerReview(BaseModel):
    ReviewID: PositiveInt = Field(..., alias='ReviewID')
    CustomerID: Optional[PositiveInt] = Field(None, alias='CustomerID')
    ProductID: Optional[PositiveInt] = Field(None, alias='ProductID')
    Rating: Optional[int] = Field(None, alias='Rating', ge=1, le=5) # E.g., 1-5 stars
    ReviewText: Optional[str] = Field(None, alias='ReviewText')
    ReviewDate: Optional[datetime] = Field(None, alias='ReviewDate')
    SentimentScore: Optional[float] = Field(None, alias='SentimentScore') # Numerical score
    SentimentLabel: Optional[str] = Field(None, alias='SentimentLabel') # E.g., Positive, Negative

# Example usage (optional, for testing purposes):
# if __name__ == "__main__":
#     customer_data = {
#         "CustomerID": 1,
#         "FirstName": "John",
#         "LastName": "Doe",
#         "Email": "john.doe@example.com",
#         "RegistrationDate": datetime.now()
#     }
#     customer = Customer(**customer_data)
#     print(customer.json(indent=2))

#     product_data = {
#         "ProductID": 101,
#         "ProductName": "Laptop",
#         "Price": 1200.50,
#         "StockQuantity": 0, # Test NonNegativeInt
#         "DateAdded": datetime.now()
#     }
#     product = Product(**product_data)
#     print(product.json(indent=2))

#     order_item_data = {
#         "OrderItemID": 1,
#         "OrderID": 1,
#         "ProductID": 1,
#         "Quantity": 0, # Test NonNegativeInt
#         "UnitPrice": 10.0, # Test NonNegativeFloat
#         "TotalPrice": 0.0 # Test NonNegativeFloat
#     }
#     order_item = OrderItem(**order_item_data)
#     print(order_item.json(indent=2))

#     review_data = {
#         "ReviewID": 1,
#         "CustomerID":1,
#         "ProductID":1,
#         "Rating": 5 
#     }
#     review = CustomerReview(**review_data)
#     print(review.json(indent=2))
#     try:
#         invalid_review_data = {
#             "ReviewID": 2,
#             "CustomerID":1,
#             "ProductID":1,
#             "Rating": 0 # Invalid rating
#         }
#         invalid_review = CustomerReview(**invalid_review_data)
#     except ValueError as e:
#         print(f"\nError for invalid review: {e}")

#     try:
#         invalid_product_data = {
#             "ProductID": 0, # Invalid ProductID
#             "ProductName": "Test"
#         }
#         invalid_product = Product(**invalid_product_data)
#     except ValueError as e:
#         print(f"\nError for invalid product: {e}")
