"""
ProductRepository — truy vấn Products/ProductImages phục vụ nhu cầu gửi ảnh sản phẩm
cho khách khi được yêu cầu (xem services/chat_service.py::_resolve_product_images).
"""

from sqlalchemy.orm import Session

from entity.product_image import ProductImage


class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_images_for_products(self, product_ids: list[int]) -> dict[int, list[ProductImage]]:
        """
        @desc Lấy toàn bộ ảnh của các sản phẩm được chỉ định, mỗi sản phẩm được sắp theo
        is_primary trước rồi tới sort_order — dùng để gửi nhiều ảnh khi khách yêu cầu xem ảnh.
        @params product_ids (list[int]): Danh sách ID sản phẩm cần lấy ảnh
        @return dict[int, list[ProductImage]]: Map product_id -> danh sách ProductImage đã sắp xếp
        """
        if not product_ids:
            return {}

        images = (
            self.db.query(ProductImage)
            .filter(ProductImage.product_id.in_(product_ids))
            .order_by(ProductImage.product_id, ProductImage.is_primary.desc(), ProductImage.sort_order.asc())
            .all()
        )

        result: dict[int, list[ProductImage]] = {}
        for img in images:
            result.setdefault(img.product_id, []).append(img)
        return result
