from chromadb import Collection

from constants.constants import COLLECTION_OVERVIEW, COLLECTION_SPECS, COLLECTION_REVIEWS
from database.vector_db_manager import VectorDBManager

_manager = VectorDBManager()

def get_chroma_client():
    """
    @desc Trả về đối tượng client ChromaDB từ VectorDBManager singleton
    @return ChromaClient: Client ChromaDB đang được sử dụng
    """
    return _manager.client


def get_overview_collection() -> Collection:
    """
    @desc Lấy collection ChromaDB chứa dữ liệu tổng quan sản phẩm
    @return Collection: Collection tổng quan sản phẩm
    """
    return _manager.get_collection(COLLECTION_OVERVIEW)


def get_specs_collection() -> Collection:
    """
    @desc Lấy collection ChromaDB chứa dữ liệu thông số kỹ thuật sản phẩm
    @return Collection: Collection thông số kỹ thuật sản phẩm
    """
    return _manager.get_collection(COLLECTION_SPECS)


def get_reviews_collection() -> Collection:
    """
    @desc Lấy collection ChromaDB chứa dữ liệu đánh giá sản phẩm
    @return Collection: Collection đánh giá sản phẩm
    """
    return _manager.get_collection(COLLECTION_REVIEWS)


def get_all_collections() -> dict[str, Collection]:
    """
    @desc Lấy toàn bộ các collection ChromaDB dưới dạng dictionary ánh xạ tên sang collection
    @return dict[str, Collection]: Dictionary với key là tên collection và value là đối tượng Collection
    """
    return _manager.get_all_collections()
