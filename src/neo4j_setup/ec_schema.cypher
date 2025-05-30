// Neo4j Schema for E-commerce (EC) System Entities
// This file outlines the node labels and their properties as described in
// section 4.1 of the data_schema_and_transformation_proposal.md.
// Data types are harmonized with src/data_models/ec_models.py.

// Node: ECCustomer
// Label: ECCustomer
// Properties:
//   customerID: Integer (Primary Key, from Pydantic Customer.CustomerID: PositiveInt)
//   firstName: String (from Pydantic Customer.FirstName: Optional[str])
//   lastName: String (from Pydantic Customer.LastName: Optional[str])
//   email: String (from Pydantic Customer.Email: Optional[EmailStr])
//   phoneNumber: String (from Pydantic Customer.PhoneNumber: Optional[str])
//   shippingAddress: String (from Pydantic Customer.ShippingAddress: Optional[str])
//   billingAddress: String (from Pydantic Customer.BillingAddress: Optional[str])
//   registrationDate: Datetime (from Pydantic Customer.RegistrationDate: Optional[datetime])
//   lastLoginDate: Datetime (from Pydantic Customer.LastLoginDate: Optional[datetime])

// Node: Product
// Label: Product
// Properties:
//   productID: Integer (Primary Key, from Pydantic Product.ProductID: PositiveInt)
//   productName: String (from Pydantic Product.ProductName: Optional[str])
//   description: String (from Pydantic Product.Description: Optional[str])
//   sku: String (from Pydantic Product.SKU: Optional[str])
//   price: Float (from Pydantic Product.Price: Optional[NonNegativeFloat])
//   stockQuantity: Integer (from Pydantic Product.StockQuantity: Optional[NonNegativeInt])
//   imagePath: String (from Pydantic Product.ImagePath: Optional[str])
//   dateAdded: Datetime (from Pydantic Product.DateAdded: Optional[datetime])
// Note: Product.CategoryID and Product.SupplierID from the conceptual schema (section 1.1)
// are modeled as relationships in Neo4j (e.g., -[:BELONGS_TO]->(Category), -[:SUPPLIED_BY]->(Supplier))
// and are not direct properties of the Product node itself, as per section 4.1.

// Node: Category
// Label: Category
// Properties:
//   categoryID: Integer (Primary Key, from Pydantic Category.CategoryID: PositiveInt)
//   categoryName: String (from Pydantic Category.CategoryName: Optional[str])
//   description: String (from Pydantic Category.Description: Optional[str])

// Node: Order
// Label: Order
// Properties:
//   orderID: Integer (Primary Key, from Pydantic Order.OrderID: PositiveInt)
//   orderDate: Datetime (from Pydantic Order.OrderDate: Optional[datetime])
//   orderStatus: String (from Pydantic Order.OrderStatus: Optional[str])
//   totalAmount: Float (from Pydantic Order.TotalAmount: Optional[NonNegativeFloat])
//   shippingAddress: String (from Pydantic Order.ShippingAddress: Optional[str])
//   billingAddress: String (from Pydantic Order.BillingAddress: Optional[str])
// Note: Order.CustomerID from the conceptual schema (section 1.1) is modeled as a
// relationship in Neo4j (e.g., -[:PLACED_BY]->(ECCustomer) or (ECCustomer)-[:PLACED]->(Order))
// and is not a direct property of the Order node itself, as per section 4.1.

// Node: Supplier
// Label: Supplier
// Properties:
//   supplierID: Integer (Primary Key, from Pydantic Supplier.SupplierID: PositiveInt)
//   supplierName: String (from Pydantic Supplier.SupplierName: Optional[str])
//   contactPerson: String (from Pydantic Supplier.ContactPerson: Optional[str])
//   email: String (from Pydantic Supplier.Email: Optional[EmailStr])
//   phoneNumber: String (from Pydantic Supplier.PhoneNumber: Optional[str])

// Node: Review
// Label: Review
// Properties:
//   reviewID: Integer (Primary Key, from Pydantic CustomerReview.ReviewID: PositiveInt)
//   rating: Integer (from Pydantic CustomerReview.Rating: Optional[int], ge=1, le=5)
//   reviewText: String (from Pydantic CustomerReview.ReviewText: Optional[str])
//   reviewDate: Datetime (from Pydantic CustomerReview.ReviewDate: Optional[datetime])
//   sentimentScore: Float (from Pydantic CustomerReview.SentimentScore: Optional[float])
//   sentimentLabel: String (from Pydantic CustomerReview.SentimentLabel: Optional[str])
// Note: CustomerReview.CustomerID and CustomerReview.ProductID from the conceptual schema (section 1.1)
// are modeled as relationships in Neo4j (e.g., (ECCustomer)-[:WROTE]->(Review), (Product)-[:HAS_REVIEW]->(Review))
// and are not direct properties of the Review node itself, as per section 4.1.

// --- Optional: Example Cypher statements for creating constraints ---
// The following section with actual Cypher commands for constraints and indexes
// supersedes these commented out examples.
/*
CREATE CONSTRAINT IF NOT EXISTS FOR (c:ECCustomer) REQUIRE c.customerID IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (p:Product) REQUIRE p.productID IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (cat:Category) REQUIRE cat.categoryID IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (o:Order) REQUIRE o.orderID IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (s:Supplier) REQUIRE s.supplierID IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (rev:Review) REQUIRE rev.reviewID IS UNIQUE;
*/

// --- End of Node Schema Definition ---

// --- Neo4j Schema for E-commerce (EC) System Relationships ---
// Based on section 4.2 of data_schema_and_transformation_proposal.md
// and src/data_models/ec_models.py for property types.

// Relationship: PLACED
// Type: (ECCustomer) -[:PLACED]-> (Order)
// Properties:
//   date: Datetime (Corresponds to Pydantic Order.OrderDate: Optional[datetime].
//                  Proposal notes this is redundant if on Order node but can mark relationship time.)

// Relationship: CONTAINS
// Type: (Order) -[:CONTAINS]-> (Product)
// Properties:
//   quantity: Integer (Corresponds to Pydantic OrderItem.Quantity: Optional[NonNegativeInt])
//   unitPrice: Float (Corresponds to Pydantic OrderItem.UnitPrice: Optional[NonNegativeFloat])

// Relationship: BELONGS_TO
// Type: (Product) -[:BELONGS_TO]-> (Category)
// Properties: None specified in proposal 4.2

// Relationship: SUPPLIED_BY
// Type: (Product) -[:SUPPLIED_BY]-> (Supplier)
// Properties: None specified in proposal 4.2

// Relationship: WROTE_REVIEW
// Type: (ECCustomer) -[:WROTE_REVIEW]-> (Review)
// Properties: None specified in proposal 4.2

// Relationship: HAS_REVIEW
// Type: (Product) -[:HAS_REVIEW]-> (Review)
// Properties: None specified in proposal 4.2

// --- End of Relationship Schema Definition ---

// --- Constraints and Indexes ---
// These are runnable Cypher commands.
// Use `IF NOT EXISTS` for idempotency, allowing the script to be run multiple times.

// Unique Constraints for Primary Keys:
CREATE CONSTRAINT IF NOT EXISTS FOR (c:ECCustomer) REQUIRE c.customerID IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (p:Product) REQUIRE p.productID IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (cat:Category) REQUIRE cat.categoryID IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (o:Order) REQUIRE o.orderID IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (s:Supplier) REQUIRE s.supplierID IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (r:Review) REQUIRE r.reviewID IS UNIQUE;

// Indexes for Frequently Queried Properties:
CREATE INDEX IF NOT EXISTS FOR (c:ECCustomer) ON (c.email);
CREATE INDEX IF NOT EXISTS FOR (p:Product) ON (p.productName);
CREATE INDEX IF NOT EXISTS FOR (cat:Category) ON (cat.categoryName);
CREATE INDEX IF NOT EXISTS FOR (s:Supplier) ON (s.supplierName);

// --- End of Constraints and Indexes ---
