README.md コンテンツ
# BOPIS/POS Application

## Description
This application aims to streamline Buy Online, Pick up In Store (BOPIS) operations and provide basic Point of Sale (POS) capabilities, particularly useful for events or retail environments. It is designed with a multi-tenant architecture to support various vendors or events simultaneously.

## Core Features (Initial Phase)
The initial phase will focus on the following core features:
*   User Registration and Login (for customers, staff, tenant admins, super admin)
*   Multi-Tenant Support
*   Online Order Placement (BOPIS)
*   QR Code Generation for Orders
*   QR Code Scanning for Order Pickup Verification
*   Staff Interface for Order Management
*   Simplified POS Functionality for In-Person Sales

## Technology Stack (Intended)
*   **Backend:** Python, SQLAlchemy (ORM)
*   **Web Framework:** Flask / Django (or similar)
*   **Database:** PostgreSQL / MySQL (or similar relational database)
*   **Frontend:** HTML, CSS, JavaScript (potentially with a light framework for staff UI)
*   **QR Code Generation:** A Python library like `qrcode`

## Current Status
This project is currently in the conceptual design and detailed planning phase. Implementation of the described features is pending resolution of environment setup issues that currently prevent file creation and code execution.
製品要件ドキュメント（PRD）の内容
1.  Introduction
    1.1. Purpose: This document outlines the product requirements for the initial phase of the BOPIS/POS Application. It serves as a guide for stakeholders and the development team to ensure a shared understanding of the product's goals, features, and target users.
    1.2. Project Vision: To provide a comprehensive, efficient, and user-friendly SaaS (Software as a Service) solution for managing Buy Online, Pick up In Store (BOPIS) processes and event-based Point of Sale (POS) transactions, catering to multiple tenants with diverse needs.
    1.3. Goals for Initial Phase:
        *   Successfully implement the core BOPIS workflow, from online order placement to QR code-based pickup.
        *   Enable basic POS transaction capabilities for in-person sales.
        *   Establish a robust multi-tenant foundation to support isolated tenant operations.
        *   Implement secure user authentication and role-based access control.
        *   Develop a functional Minimum Viable Product (MVP) for the staff-facing interface to manage orders and POS.

2.  Target Users
    2.1. Customers (End-Users):
        *   Needs: Easily browse products, place orders online for pickup, view order history, and have a quick and secure pickup experience using a QR code.
    2.2. Staff Members:
        *   Needs: Efficiently view and manage incoming BOPIS orders, update order statuses, scan customer QR codes for verification, process in-person POS sales quickly, and have a clear, intuitive interface.
    2.3. Tenant Administrators:
        *   Needs: Manage their specific store/event operations, including adding/managing products, managing staff accounts for their tenant, viewing tenant-specific orders and basic reports, and configuring tenant-specific settings.
    2.4. Super Administrator:
        *   Needs: Manage the overall platform, including creating and managing tenant accounts, assigning tenant administrators, and having an overview of platform usage (future).

3.  Functional Requirements (Initial Phase)
    3.1. Multi-Tenancy
        *   FR1: The system must support multiple tenants, with each tenant's data (products, orders, staff, customers if tenant-specific) logically isolated.
        *   FR2: Super Admin can create and manage tenant accounts.
    3.2. User Authentication & Authorization
        *   FR3: Users can register for an account (Customers primarily; Tenant Admins might be created by Super Admin or via a separate flow; Staff created by Tenant Admins).
        *   FR4: Registered users can log in using their credentials (email/username and password).
        *   FR5: Passwords must be securely hashed and stored.
        *   FR6: The system must support distinct user roles: Customer, Staff, Tenant Admin, Super Admin.
        *   FR7: Access to features and data must be restricted based on user roles (e.g., staff cannot access tenant management functions).
        *   FR8: Users can log out of the system.
        *   FR9: Session management will ensure users remain logged in for a defined period or until logout.
    3.3. Product Management (Basic for Initial Phase by Tenant Admin)
        *   FR10: Tenant Admins can add new products with details like name, description, price, SKU (unique per tenant), and initial stock quantity.
        *   FR11: Tenant Admins can view a list of their products.
        *   FR12: Tenant Admins can edit existing product details.
        *   FR13: Tenant Admins can update stock quantities for products.
    3.4. BOPIS - Online Ordering (Customer Flow)
        *   FR14: Customers can browse/search products available for their selected tenant/event.
        *   FR15: Customers can add products to a shopping cart, view, and modify cart contents (update quantity, remove item).
        *   FR16: The shopping cart should persist for logged-in users across sessions (basic).
        *   FR17: Customers can proceed to a checkout process.
        *   FR18: Checkout includes order summary, (mock) payment processing, and order confirmation.
        *   FR19: Upon successful order confirmation and (mock) payment, a unique QR code (or a reference to it) is generated and made available to the customer (e.g., displayed on screen, sent via email).
        *   FR20: Customers can view their current and past order history with statuses.
    3.5. BOPIS - Order Fulfillment (Staff Flow)
        *   FR21: Staff members (associated with a tenant) can view a list of BOPIS orders for their tenant.
        *   FR22: Staff can filter/sort orders (e.g., by status, date).
        *   FR23: Staff can view details of a specific order.
        *   FR24: Staff can update the status of an order (e.g., "Order Confirmed" -> "Processing/Being Picked" -> "Ready for Pickup" -> "Completed" -> "Cancelled").
        *   FR25: Staff can use a QR code scanning interface to scan customer's QR code.
        *   FR26: Upon successful QR scan, the system verifies the order, displays its details, and allows staff to mark the order as "Completed."
        *   FR27: Inventory levels are updated (decremented) when an order is confirmed or marked as picked.
    3.6. POS - In-Person Sales (Simplified Staff Flow)
        *   FR28: Staff can initiate a new POS transaction from their interface.
        *   FR29: Staff can select products to add to the POS sale (e.g., from a catalog view).
        *   FR30: Staff can manage the cart for the POS sale (add, remove, update quantity).
        *   FR31: Staff can process (mock) payments for POS sales (e.g., record as "Cash" or "Card").
        *   FR32: Upon successful (mock) payment, the POS order is recorded and marked as "Completed."
        *   FR33: POS orders are distinguishable from BOPIS orders (e.g., by an order type field).
        *   FR34: Inventory levels are updated for products sold via POS.
    3.7. Staff Application Interface (Basic)
        *   FR35: Staff members log in through a dedicated login screen.
        *   FR36: A simple dashboard provides access to core functionalities (Order Management, QR Scanner, POS).
        *   FR37: The interface is intuitive and easy to navigate for performing primary tasks.

4.  Non-Functional Requirements (Briefly for Initial Phase)
    *   NFR1: Usability: The application should be intuitive and easy to use for all target user roles. Error messages should be clear.
    *   NFR2: Security: User passwords must be stored securely (hashed). Communication should ideally be over HTTPS (assumed for a web app). QR codes should not directly expose sensitive PII; use opaque tokens. Basic role-based access control must be enforced.
    *   NFR3: Reliability: Core order processing (BOPIS and POS) and inventory updates should be accurate and reliable.

5.  Out of Scope for Initial Phase (Examples)
    *   Real payment gateway integration.
    *   Advanced reporting and analytics dashboards.
    *   Advanced inventory management (e.g., purchase orders, stock transfers, low stock alerts).
    *   Marketing and promotional features (e.g., discount codes, loyalty programs).
    *   Full offline capabilities for order processing or POS.
    *   Hardware integration (e.g., receipt printers, physical POS terminals).
    *   Customer self-service for returns or complex order modifications.
    *   User profile management beyond basic login/logout.
    *   Shipping/delivery options.
技術仕様書（TSD）の内容
1.  Introduction
    1.1. Purpose: This document details the technical design and specifications for the initial phase (MVP) of the BOPIS/POS Application. It is intended for the development team to guide implementation.
    1.2. Scope: This TSD covers the core features defined in the PRD for the initial phase, including multi-tenancy, user authentication, BOPIS order flow, simplified POS, and the underlying database structure.

2.  System Architecture Overview
    2.1. High-Level Architecture: The system will be a web-based application comprising:
        *   Web Application Server: Handles business logic, API requests, and potentially serves frontend components.
        *   Database: Stores all persistent data.
        *   REST API: Primary interface for communication between frontend clients (customer-facing web, staff app) and the backend server.
    2.2. Technology Stack (Recommended):
        *   Backend: Python 3.x with FastAPI web framework (for its performance, ease of use, and automatic data validation/API docs).
        *   ORM: SQLAlchemy (with Alembic for database migrations).
        *   Password Hashing: `passlib` library with bcrypt or Argon2.
        *   JWT Handling: `python-jose` library.
        *   Database: PostgreSQL (recommended for its robustness and features).
        *   Frontend (Staff App): Vue.js or React (for a responsive and interactive single-page application experience).
        *   Frontend (Customer-facing BOPIS): Can start with server-rendered templates (e.g., Jinja2 with FastAPI) for simplicity, or also use Vue.js/React.
        *   QR Code Generation: `qrcode` Python library (for generating QR code images or data).

3.  Database Design
    3.1. Overview: A relational database model will be implemented using SQLAlchemy as the ORM.
    3.2. Data Models (SQLAlchemy):

        ```python
        from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Numeric, ForeignKey, Text, Enum
        from sqlalchemy.orm import relationship, declarative_base
        from sqlalchemy.sql import func
        import enum

        Base = declarative_base()

        class UserRole(enum.Enum):
            customer = "customer"
            staff = "staff"
            tenant_admin = "tenant_admin"
            super_admin = "super_admin"

        class OrderType(enum.Enum):
            BOPIS = "BOPIS"
            POS_SALE = "POS_SALE"

        class OrderStatus(enum.Enum):
            CART = "CART" # Temporary state before checkout
            PENDING_PAYMENT = "PENDING_PAYMENT"
            PAYMENT_FAILED = "PAYMENT_FAILED"
            ORDER_CONFIRMED = "ORDER_CONFIRMED" # Payment successful
            PROCESSING = "PROCESSING"
            READY_FOR_PICKUP = "READY_FOR_PICKUP"
            COMPLETED = "COMPLETED" # Picked up or POS sale finalized
            CANCELLED = "CANCELLED"
            REFUNDED = "REFUNDED" # Future state

        class PaymentStatus(enum.Enum):
            UNPAID = "UNPAID"
            PAID = "PAID"
            FAILED = "FAILED"
            REFUNDED = "REFUNDED" # Future state

        class Tenant(Base):
            __tablename__ = 'tenants'
            id = Column(Integer, primary_key=True, index=True)
            name = Column(String, unique=True, index=True, nullable=False)
            created_at = Column(DateTime(timezone=True), server_default=func.now())

            users = relationship("User", back_populates="tenant")
            products = relationship("Product", back_populates="tenant")
            orders = relationship("Order", back_populates="tenant")

        class User(Base):
            __tablename__ = 'users'
            id = Column(Integer, primary_key=True, index=True)
            username = Column(String, unique=True, index=True, nullable=False) # Could be email
            email = Column(String, unique=True, index=True, nullable=False)
            password_hash = Column(String, nullable=False)
            role = Column(Enum(UserRole), nullable=False)
            tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=True) # Null for super_admin, staff/tenant_admin must have it
            created_at = Column(DateTime(timezone=True), server_default=func.now())
            is_active = Column(Boolean, default=True)

            tenant = relationship("Tenant", back_populates="users")
            orders = relationship("Order", back_populates="customer") # Orders placed by this user

        class Product(Base):
            __tablename__ = 'products'
            id = Column(Integer, primary_key=True, index=True)
            name = Column(String, nullable=False)
            description = Column(Text, nullable=True)
            price = Column(Numeric(10, 2), nullable=False) # Assuming 2 decimal places for currency
            sku = Column(String, index=True, nullable=False) # Should be unique per tenant
            tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
            stock_quantity = Column(Integer, default=0, nullable=False)
            image_url = Column(String, nullable=True)
            created_at = Column(DateTime(timezone=True), server_default=func.now())
            updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

            # __table_args__ = (UniqueConstraint('sku', 'tenant_id', name='_sku_tenant_uc'),) # Enforce SKU uniqueness per tenant at DB level

            tenant = relationship("Tenant", back_populates="products")
            order_items = relationship("OrderItem", back_populates="product")

        class Order(Base):
            __tablename__ = 'orders'
            id = Column(Integer, primary_key=True, index=True)
            user_id = Column(Integer, ForeignKey('users.id'), nullable=False) # Customer who placed order / staff for POS
            tenant_id = Column(Integer, ForeignKey('tenants.id'), nullable=False)
            
            order_type = Column(Enum(OrderType), nullable=False, default=OrderType.BOPIS)
            status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.CART)
            payment_status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.UNPAID)
            
            total_amount = Column(Numeric(10, 2), nullable=False)
            pickup_token = Column(String, unique=True, index=True, nullable=True) # For QR code BOPIS pickup
            
            created_at = Column(DateTime(timezone=True), server_default=func.now())
            updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
            
            # For BOPIS, might include preferred pickup time if that feature is added
            # pickup_scheduled_time = Column(DateTime(timezone=True), nullable=True)
            # For POS, might include staff_id who processed the sale
            # processed_by_staff_id = Column(Integer, ForeignKey('users.id'), nullable=True)

            customer = relationship("User", back_populates="orders")
            tenant = relationship("Tenant", back_populates="orders")
            order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

        class OrderItem(Base):
            __tablename__ = 'order_items'
            id = Column(Integer, primary_key=True, index=True)
            order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
            product_id = Column(Integer, ForeignKey('products.id'), nullable=False) 
            quantity = Column(Integer, nullable=False)
            price_at_purchase = Column(Numeric(10, 2), nullable=False) # Price of product at the time of order

            order = relationship("Order", back_populates="order_items")
            product = relationship("Product", back_populates="order_items")

        ```
    3.3. Relationships:
        *   Tenant to User: One-to-Many (a tenant has many users; a user belongs to one tenant, except super_admin).
        *   Tenant to Product: One-to-Many.
        *   Tenant to Order: One-to-Many.
        *   User (Customer) to Order: One-to-Many.
        *   Order to OrderItem: One-to-Many (an order comprises multiple items).
        *   Product to OrderItem: One-to-Many.

4.  Core Feature Technical Specifications
    4.1. Multi-Tenancy Implementation Strategy:
        *   Tenant Context: Determined primarily from the authenticated user's `tenant_id`. For public-facing pages (like product browsing before login), tenant might be identified via subdomain (e.g., `tenant1.app.com`) or URL path (`app.com/tenant1/`).
        *   Data Scoping: All database queries for tenant-specific data (products, orders, staff users) will include a `WHERE tenant_id = :current_tenant_id` clause, enforced by API logic and possibly SQLAlchemy query helpers.
    4.2. User Authentication and Authorization:
        *   Registration: User provides details; password hashed using `passlib` (bcrypt/Argon2). `User` record created.
        *   Login: User provides credentials; password verified using `passlib`. Upon success, a JWT is generated.
        *   Session Management (JWT):
            *   Token Generation: Using `python-jose`.
            *   Claims: `sub` (user_id), `role` (user_role), `tenant_id` (if applicable), `exp` (expiry time).
            *   Storage/Transmission: Token sent to client via JSON response. Client stores it (e.g., localStorage, secure cookie for web) and sends it in `Authorization: Bearer <token>` header for subsequent requests.
        *   Role-Based Access Control (RBAC): FastAPI dependencies will be used to protect endpoints. These dependencies will decode the JWT, verify its validity, and check if the user's role (from token claims) is permitted for the requested operation.
    4.3. Product Management:
        *   Standard CRUD REST endpoints for products (e.g., `/products/`, `/products/{product_id}`).
        *   All operations strictly scoped by the `tenant_id` of the authenticated Tenant Admin.
        *   Ensure SKU uniqueness per tenant (DB constraint preferred, fallback to application-level check).
    4.4. BOPIS - Online Ordering:
        *   Cart Management: For logged-in users, cart can be stored server-side (e.g., linked to user_id, or an order with status 'CART'). For guest users, client-side storage (e.g., localStorage) can be used, with cart contents transferred to server upon login or checkout initiation.
        *   Order Creation: An atomic transaction will create the `Order` and associated `OrderItem` records. Payment status initially 'UNPAID', order status 'PENDING_PAYMENT'. After (mock) payment, status moves to 'ORDER_CONFIRMED'.
        *   Inventory Decrement: Stock quantity for products will be decremented upon successful order confirmation. Need to handle potential race conditions or insufficient stock scenarios (e.g., optimistic locking or check-then-decrement).
        *   QR Code Generation: A unique `pickup_token` (e.g., UUID) will be generated and stored in the `Order` model. This token (not raw order ID) will be encoded into the QR code image provided to the user.
    4.5. BOPIS - Order Fulfillment (Staff):
        *   Order Status Transitions: Endpoints for staff to update order status based on defined workflow.
        *   QR Code Scanning & Verification: Staff app scans QR, extracts `pickup_token`. An API endpoint (e.g., `/orders/verify-pickup/{pickup_token}`) validates the token, checks order status (must be 'READY_FOR_PICKUP'), verifies tenant, and if valid, updates order status to 'COMPLETED'.
    4.6. POS - In-Person Sales (Simplified):
        *   Order Creation: Staff uses an interface to add products to a cart. On finalization, an `Order` is created with `order_type` = 'POS_SALE' and `status` = 'COMPLETED' (assuming payment is immediate).
        *   Mock Payment: Staff selects payment method (e.g., "Cash", "Card"), which is recorded on the order. No actual payment processing.
        *   Inventory Update: Product `stock_quantity` is decremented immediately upon POS order finalization.

5.  API Design (Conceptual RESTful Endpoints - JSON)
    *   Auth: `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh-token`
    *   Users: `GET /users/me`, `PUT /users/me` (Limited scope for MVP)
    *   Tenants (Super Admin): `POST /tenants`, `GET /tenants`, `GET /tenants/{tenant_id}`
    *   Products (Tenant Admin): `POST /products`, `GET /products`, `GET /products/{product_id}`, `PUT /products/{product_id}` (All scoped by tenant)
    *   Cart (Customer): `GET /cart`, `POST /cart/items`, `PUT /cart/items/{item_id}`, `DELETE /cart/items/{item_id}`
    *   Orders (Customer & Staff): `POST /orders` (checkout), `GET /orders`, `GET /orders/{order_id}`
    *   Order Pickup (Staff): `POST /orders/verify-pickup` (expects pickup_token)
    *   POS (Staff): `POST /pos/orders` (create POS order)

6.  Error Handling and Logging (Briefly)
    *   Error Handling: FastAPI's exception handling mechanisms will be used to return consistent JSON error responses with appropriate HTTP status codes. Custom exception classes for domain-specific errors.
    *   Logging: Standard Python `logging` module. Log important events (e.g., order creation, status changes, errors) with timestamps and relevant 
