"""
SQLAlchemy ORM Models for Retail AI Consultation Platform
Organized by domain following database.sql structure
"""

# [1] Core Product Domain
from entity.brand import Brand
from entity.tag import Tag
from entity.category import Category
from entity.product import Product
from entity.product_image import ProductImage
from entity.product_tag import ProductTag

# [2] User Domain
from entity.user import User
from entity.user_profile import UserProfile
from entity.user_address import UserAddress

# [3] Commerce Domain
from entity.cart import Cart
from entity.cart_item import CartItem
from entity.order import Order
from entity.order_item import OrderItem
from entity.payment import Payment

# [4] Content Domain
from entity.product_review import ProductReview

# [5] AI / Consultation Domain
from entity.conversation_session import ConversationSession
from entity.conversation_message import ConversationMessage
from entity.psych_state_log import PsychStateLog
from entity.agent_performance_log import AgentPerformanceLog

# [6] Platform & Infrastructure Domain
from entity.api_key import APIKey
from entity.system_config import SystemConfig
from entity.audit_log import AuditLog

__all__ = [
    # [1] Core Product Domain
    'Brand',
    'Tag',
    'Category',
    'Product',
    'ProductImage',
    'ProductTag',

    # [2] User Domain
    'User',
    'UserProfile',
    'UserAddress',

    # [3] Commerce Domain
    'Cart',
    'CartItem',
    'Order',
    'OrderItem',
    'Payment',

    # [4] Content Domain
    'ProductReview',

    # [5] AI / Consultation Domain
    'ConversationSession',
    'ConversationMessage',
    'PsychStateLog',
    'AgentPerformanceLog',

    # [6] Platform & Infrastructure Domain
    'APIKey',
    'SystemConfig',
    'AuditLog',
]

