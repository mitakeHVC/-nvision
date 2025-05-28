# Data Schema and Transformation Proposal

This document outlines the conceptual data schemas for E-commerce (EC) and CRM systems, their relationships for Neo4j, and a vector embedding strategy for ChromaDB. This will serve as a basis for designing data ingestion and analysis engines.

## 1. Conceptual Data Schemas

### 1.1 E-commerce (EC) System

Key entities and their common attributes:

*   **Customers:**
    *   `CustomerID` (Primary Key)
    *   `FirstName`
    *   `LastName`
    *   `Email`
    *   `PhoneNumber`
    *   `ShippingAddress`
    *   `BillingAddress`
    *   `RegistrationDate`
    *   `LastLoginDate`
*   **Products:**
    *   `ProductID` (Primary Key)
    *   `ProductName`
    *   `Description`
    *   `SKU`
    *   `CategoryID`
    *   `SupplierID`
    *   `Price`
    *   `StockQuantity`
    *   `ImagePath`
    *   `DateAdded`
*   **Categories:** (Product Categories)
    *   `CategoryID` (Primary Key)
    *   `CategoryName`
    *   `Description`
*   **Orders:**
    *   `OrderID` (Primary Key)
    *   `CustomerID` (Foreign Key)
    *   `OrderDate`
    *   `OrderStatus` (e.g., Pending, Shipped, Delivered, Cancelled)
    *   `TotalAmount`
    *   `ShippingAddress` (at the time of order)
    *   `BillingAddress` (at the time of order)
*   **OrderItems:** (Line items within an order)
    *   `OrderItemID` (Primary Key)
    *   `OrderID` (Foreign Key)
    *   `ProductID` (Foreign Key)
    *   `Quantity`
    *   `UnitPrice` (at the time of order)
    *   `TotalPrice`
*   **Suppliers:**
    *   `SupplierID` (Primary Key)
    *   `SupplierName`
    *   `ContactPerson`
    *   `Email`
    *   `PhoneNumber`
*   **CustomerReviews:**
    *   `ReviewID` (Primary Key)
    *   `CustomerID` (Foreign Key)
    *   `ProductID` (Foreign Key)
    *   `Rating` (e.g., 1-5 stars)
    *   `ReviewText`
    *   `ReviewDate`
    *   `SentimentScore` (Numerical score from sentiment analysis)
    *   `SentimentLabel` (e.g., Positive, Negative, Neutral)

### 1.2 CRM (Customer Relationship Management) System

Key entities and their common attributes:

*   **Contacts:** (Individuals)
    *   `ContactID` (Primary Key)
    *   `FirstName`
    *   `LastName`
    *   `Email`
    *   `PhoneNumber`
    *   `JobTitle`
    *   `CompanyID` (Foreign Key)
    *   `LeadSource`
    *   `DateCreated`
    *   `LastContactedDate`
*   **Companies:** (Organizations)
    *   `CompanyID` (Primary Key)
    *   `CompanyName`
    *   `Industry`
    *   `Website`
    *   `Address`
    *   `PhoneNumber`
    *   `AnnualRevenue`
    *   `NumberOfEmployees`
*   **Interactions:** (Activities, e.g., calls, emails, meetings)
    *   `InteractionID` (Primary Key)
    *   `ContactID` (Foreign Key)
    *   `CompanyID` (Foreign Key, optional, could be derived via Contact)
    *   `InteractionType` (e.g., Email, Call, Meeting, Note)
    *   `InteractionDate`
    *   `Subject`
    *   `Notes` (Text content of the interaction)
    *   `AssignedToUserID` (CRM User)
*   **Deals/Opportunities:**
    *   `DealID` (Primary Key)
    *   `DealName`
    *   `CompanyID` (Foreign Key)
    *   `PrimaryContactID` (Foreign Key)
    *   `Stage` (e.g., Qualification, Proposal, Negotiation, Closed Won, Closed Lost)
    *   `Amount`
    *   `ExpectedCloseDate`
    *   `AssignedToUserID` (CRM User)
*   **Users:** (CRM System Users/Sales Reps)
    *   `UserID` (Primary Key)
    *   `FirstName`
    *   `LastName`
    *   `Email`

### 1.3 Shared/Support System Entities (Potentially spanning EC & CRM)

*   **ChatSessions:**
    *   `ChatSessionID` (Primary Key)
    *   `CustomerID` (Foreign Key, from EC)
    *   `ContactID` (Foreign Key, from CRM, if applicable and identified)
    *   `UserID` (Foreign Key, CRM User/Support Agent)
    *   `StartTime`
    *   `EndTime`
    *   `Platform` (e.g., Web, Mobile App)
*   **ChatMessages:**
    *   `ChatMessageID` (Primary Key)
    *   `ChatSessionID` (Foreign Key)
    *   `SenderID` (Could be CustomerID or UserID)
    *   `SenderType` (e.g., 'Customer', 'Agent')
    *   `MessageText`
    *   `Timestamp`
    *   `ExtractedKeywords` (List of strings)
    *   `ClassifiedTopics` (List of strings)

## 2. Relationship Mapping for Neo4j

Potential relationships between entities from both EC and CRM systems:

**E-commerce Relationships:**

*   `CUSTOMER --PLACED--> ORDER`
*   `ORDER --CONTAINS--> PRODUCT` (via OrderItems, properties: `Quantity`, `UnitPrice`)
*   `PRODUCT --BELONGS_TO--> CATEGORY`
*   `PRODUCT --SUPPLIED_BY--> SUPPLIER`
*   `CUSTOMER --HAS_SHIPPING_ADDRESS--> ADDRESS` (if addresses are separate nodes)
*   `CUSTOMER --HAS_BILLING_ADDRESS--> ADDRESS` (if addresses are separate nodes)
*   `CUSTOMER --WROTE--> REVIEW`
*   `PRODUCT --HAS_REVIEW--> REVIEW`

**CRM Relationships:**

*   `CONTACT --WORKS_FOR--> COMPANY`
*   `CONTACT --PARTICIPATED_IN--> INTERACTION`
*   `COMPANY --HAS_INTERACTION--> INTERACTION`
*   `DEAL --ASSOCIATED_WITH--> COMPANY`
*   `DEAL --HAS_PRIMARY_CONTACT--> CONTACT`
*   `DEAL --INVOLVES_CONTACT--> CONTACT` (for other contacts involved in the deal)
*   `USER --ASSIGNED_TO--> DEAL`
*   `USER --LOGGED--> INTERACTION` (User who recorded the interaction)
*   `USER --OWNS--> CONTACT` (Lead/Contact owner)
*   `USER --OWNS--> COMPANY` (Account owner)

**Support System Relationships (Chat):**

*   `CUSTOMER --PARTICIPATED_IN--> CHAT_SESSION`
*   `CONTACT --PARTICIPATED_IN--> CHAT_SESSION` (if linked)
*   `USER --HANDLED--> CHAT_SESSION` (Support Agent)
*   `CHAT_SESSION --HAS_MESSAGE--> CHAT_MESSAGE`
*   `(CUSTOMER|USER) --SENT_MESSAGE--> CHAT_MESSAGE` (Indicates who sent the message)


**Cross-System Relationships (EC & CRM):**

*   `EC_CUSTOMER --IS_SAME_AS--> CRM_CONTACT` (Identity resolution needed)
*   `EC_CUSTOMER --IS_LINKED_TO--> CRM_COMPANY` (e.g. B2B customer)
*   `ORDER --INITIATED_FROM_INTERACTION--> CRM_INTERACTION` (e.g. order placed after a sales call)
*   `PRODUCT --MENTIONED_IN--> CRM_INTERACTION`

## 3. Vector Embedding Strategy for ChromaDB

Identify text-based attributes for creating vector embeddings and define composite document strategy.

**Attributes for Embedding:**

*   **EC System:**
    *   `Product.ProductName`
    *   `Product.Description`
    *   `Category.CategoryName`
    *   `Category.Description`
    *   `CustomerReview.ReviewText`
*   **CRM System:**
    *   `Interaction.Subject`
    *   `Interaction.Notes`
    *   `Deal.DealName`
    *   `Company.CompanyName` (less critical but can help find similar companies by name)
    *   `Company.Industry` (can be embedded if it's free-text, otherwise used as metadata)
*   **Shared/Support System:**
    *   `ChatMessage.MessageText` (or summaries of conversations)

**Composite Document Strategy:**

*   **Product Embeddings:**
    *   Combine `Product.ProductName` and `Product.Description`.
    *   Optionally, include `Category.CategoryName` to provide context.
    *   Example: "Product: [ProductName], Description: [Description], Category: [CategoryName]"
*   **Interaction Embeddings:**
    *   Combine `Interaction.Subject` and `Interaction.Notes`.
    *   Optionally, include `InteractionType` as metadata or part of the text.
    *   Example: "Interaction Type: [InteractionType], Subject: [Subject], Notes: [Notes]"
*   **Customer/Contact Profile Embeddings (Advanced):**
    *   Aggregate notes from multiple interactions for a `Contact` or `Customer` to create a profile embedding representing their interests or issues.
    *   Example for a Contact: "Contact: [FirstName] [LastName]. Interactions Summary: [Note 1 snippet]...[Note N snippet]"
*   **Company Profile Embeddings (Advanced):**
    *   Aggregate notes from interactions related to a `Company`.
    *   Combine with `Company.Industry` or other descriptive fields.
    *   Example: "Company: [CompanyName], Industry: [Industry]. Interactions Summary: [Note 1 snippet]...[Note N snippet]"
*   **Review Embeddings:**
    *   Embed `CustomerReview.ReviewText`.
    *   Example: "Review: [ReviewText]"
*   **Chat Message/Session Embeddings:**
    *   Embed individual `ChatMessage.MessageText` or a concatenation/summary of messages within a `ChatSession`.
    *   If embedding whole sessions: "Chat Session with [CustomerName/ID] and Agent [AgentName/ID]: [Message 1 text] [Message 2 text] ..."
    *   If embedding individual messages: "Chat Message from [SenderType]: [MessageText]"

**Metadata for ChromaDB:**

Along with the vector embeddings, store relevant metadata for filtering and context.

*   For Product Embeddings: `ProductID`, `CategoryID`, `Price`, `StockQuantity`.
*   For Interaction Embeddings: `InteractionID`, `ContactID`, `CompanyID`, `InteractionDate`, `InteractionType`, `AssignedToUserID`.
*   For Customer/Contact Profile Embeddings: `CustomerID`/`ContactID`.
*   For Company Profile Embeddings: `CompanyID`.
*   **For Review Embeddings:** `ReviewID`, `CustomerID`, `ProductID`, `ReviewDate`, `Rating`, `SentimentScore` (numerical), `SentimentLabel` (e.g., "positive", "negative", "neutral").
*   **For Chat Message/Session Embeddings:**
    *   If embedding individual messages: `ChatMessageID`, `ChatSessionID`, `SenderID`, `SenderType`, `Timestamp`, `ExtractedKeywords` (list), `ClassifiedTopics` (list).
    *   If embedding sessions: `ChatSessionID`, `CustomerID`, `UserID` (agent), `StartTime`, `EndTime`, `Platform`, `OverallSessionKeywords` (list), `OverallSessionTopics` (list).

## 4. Neo4j Graph Schema

Detail how entities and attributes become nodes and properties, and relationships become edges.

### 4.1 Nodes and Properties:

*   **EC_Customer Node:**
    *   Label: `Customer` (or `ECCustomer` to distinguish if CRM contacts are also `Customer`)
    *   Properties: `customerID`, `firstName`, `lastName`, `email`, `phoneNumber`, `shippingAddress`, `billingAddress`, `registrationDate`, `lastLoginDate`.
*   **Product Node:**
    *   Label: `Product`
    *   Properties: `productID`, `productName`, `description`, `sku`, `price`, `stockQuantity`, `imagePath`, `dateAdded`.
*   **Category Node:**
    *   Label: `Category`
    *   Properties: `categoryID`, `categoryName`, `description`.
*   **Order Node:**
    *   Label: `Order`
    *   Properties: `orderID`, `orderDate`, `orderStatus`, `totalAmount`, `shippingAddress`, `billingAddress`.
*   **Supplier Node:**
    *   Label: `Supplier`
    *   Properties: `supplierID`, `supplierName`, `contactPerson`, `email`, `phoneNumber`.

*   **CRM_Contact Node:**
    *   Label: `Contact` (or `CRMContact`)
    *   Properties: `contactID`, `firstName`, `lastName`, `email`, `phoneNumber`, `jobTitle`, `leadSource`, `dateCreated`, `lastContactedDate`.
*   **Company Node:**
    *   Label: `Company`
    *   Properties: `companyID`, `companyName`, `industry`, `website`, `address`, `phoneNumber`, `annualRevenue`, `numberOfEmployees`.
*   **Interaction Node:**
    *   Label: `Interaction`
    *   Properties: `interactionID`, `interactionType`, `interactionDate`, `subject`, `notes_summary` (full notes might be too large for a property, consider storing a summary or embedding ID).
*   **Deal Node:**
    *   Label: `Deal`
    *   Properties: `dealID`, `dealName`, `stage`, `amount`, `expectedCloseDate`.
*   **User Node:** (CRM User)
    *   Label: `User`
    *   Properties: `userID`, `firstName`, `lastName`, `email`.
*   **Review Node:**
    *   Label: `Review`
    *   Properties: `reviewID`, `rating`, `reviewText` (or summary/embedding ID), `reviewDate`, `sentimentScore`, `sentimentLabel`.
*   **ChatSession Node:**
    *   Label: `ChatSession`
    *   Properties: `chatSessionID`, `startTime`, `endTime`, `platform`.
*   **ChatMessage Node:**
    *   Label: `ChatMessage`
    *   Properties: `chatMessageID`, `messageText` (or summary/embedding ID), `timestamp`, `senderType`, `extractedKeywords` (list), `classifiedTopics` (list).


### 4.2 Relationships and Properties:

*   **`PLACED` Relationship:**
    *   `(Customer) -[:PLACED]-> (Order)`
    *   Properties: `date` (redundant if on Order node, but can mark the relationship time).
*   **`CONTAINS` Relationship:**
    *   `(Order) -[:CONTAINS]-> (Product)`
    *   Properties: `quantity`, `unitPrice`.
*   **`BELONGS_TO` Relationship:**
    *   `(Product) -[:BELONGS_TO]-> (Category)`
*   **`SUPPLIED_BY` Relationship:**
    *   `(Product) -[:SUPPLIED_BY]-> (Supplier)`
*   **`WORKS_FOR` Relationship:**
    *   `(Contact) -[:WORKS_FOR]-> (Company)`
    *   Properties: `startDate`, `endDate` (if applicable).
*   **`PARTICIPATED_IN` Relationship:**
    *   `(Contact) -[:PARTICIPATED_IN]-> (Interaction)`
*   **`HAS_INTERACTION` Relationship:**
    *   `(Company) -[:HAS_INTERACTION]-> (Interaction)`
*   **`ASSOCIATED_WITH` Relationship:**
    *   `(Deal) -[:ASSOCIATED_WITH]-> (Company)`
*   **`HAS_PRIMARY_CONTACT` Relationship:**
    *   `(Deal) -[:HAS_PRIMARY_CONTACT]-> (Contact)`
*   **`INVOLVES_CONTACT` Relationship:**
    *   `(Deal) -[:INVOLVES_CONTACT]-> (Contact)`
*   **`ASSIGNED_TO` Relationship:**
    *   `(User) -[:ASSIGNED_TO]-> (Deal)` (or `(Deal)-[:ASSIGNED_TO]->(User)`)
*   **`LOGGED` Relationship:**
    *   `(User) -[:LOGGED]-> (Interaction)`
*   **`OWNS` Relationship:**
    *   `(User) -[:OWNS]-> (Contact)`
    *   `(User) -[:OWNS]-> (Company)`
*   **`IS_SAME_AS` Relationship (Identity):**
    *   `(ECCustomer) -[:IS_SAME_AS {confidenceScore: float}]-> (CRMContact)`
*   **`MENTIONED_IN` Relationship:**
    *   `(Product) -[:MENTIONED_IN]-> (Interaction)`
    *   Properties: `mentionCount`.
*   **`WROTE_REVIEW` Relationship:**
    *   `(Customer) -[:WROTE_REVIEW]-> (Review)`
*   **`HAS_REVIEW` Relationship:**
    *   `(Product) -[:HAS_REVIEW]-> (Review)`
*   **`PARTICIPATED_IN_CHAT` Relationship:**
    *   `(Customer) -[:PARTICIPATED_IN_CHAT]-> (ChatSession)`
    *   `(Contact) -[:PARTICIPATED_IN_CHAT]-> (ChatSession)` (if CRM Contact is linked)
*   **`HANDLED_CHAT` Relationship:**
    *   `(User) -[:HANDLED_CHAT]-> (ChatSession)` (CRM User/Agent)
*   **`HAS_MESSAGE` Relationship:**
    *   `(ChatSession) -[:HAS_MESSAGE]-> (ChatMessage)`
    *   Properties: `sequenceNumber` (ordering messages within a session).
*   **`SENT_MESSAGE` Relationship:**
    *   `(Customer) -[:SENT_MESSAGE]-> (ChatMessage)`
    *   `(User) -[:SENT_MESSAGE]-> (ChatMessage)`

This schema provides a comprehensive starting point. Specific attributes and relationships can be refined based on available data and analytical requirements.
