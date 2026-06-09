"""
SQLAlchemy ORM Models for Retail AI Consultation Platform
Organized by domain following database.sql structure
"""

# [1] Core Product Domain
from models.brand import Brand
from models.tag import Tag
from models.category import Category
from models.product import Product
from models.product_image import ProductImage
from models.product_tag import ProductTag

# [2] User Domain
from models.user import User
from models.user_profile import UserProfile
from models.user_address import UserAddress

# [3] Commerce Domain
from models.cart import Cart
from models.cart_item import CartItem
from models.order import Order
from models.order_item import OrderItem
from models.payment import Payment

# [4] Content Domain
from models.product_review import ProductReview

# [5] AI / Consultation Domain
from models.conversation_session import ConversationSession
from models.conversation_message import ConversationMessage
from models.psych_state_log import PsychStateLog
from models.agent_performance_log import AgentPerformanceLog

# [6] Platform & Infrastructure Domain
from models.api_key import APIKey
from models.system_config import SystemConfig
from models.audit_log import AuditLog

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

