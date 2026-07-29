import chromadb
from chromadb import Collection

from constants.constants import (
    COLLECTION_OVERVIEW,
    COLLECTION_SPECS,
    COLLECTION_REVIEWS,
)
from core.config import settings
from core.logger import custom_logger

_COLLECTION_METADATA = {"hnsw:space": "cosine"}


class VectorDBManager:
    _instance = None

    def __new__(cls):
        """
        @desc Tạo hoặc trả về instance duy nhất của VectorDBManager theo pattern Singleton, khởi tạo ChromaDB client nếu chưa tồn tại
        @return VectorDBManager: Instance duy nhất của lớp VectorDBManager
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            custom_logger.info(
                f"[VectorDB] Initializing ChromaDB PersistentClient | path='{settings.CHROMA_PATH}'"
            )
            cls._instance.client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
            custom_logger.info("[VectorDB] ChromaDB client ready")
        return cls._instance

    def reset_client(self) -> None:
        """
        @desc Khởi tạo lại PersistentClient — dùng khi client trong process hiện tại đang giữ
        handle HNSW segment cũ không còn khớp với dữ liệu thật trên disk (vd: có process khác —
        script seed riêng biệt — ghi đè lên cùng thư mục CHROMA_PATH trong khi process này đang
        chạy). chromadb.PersistentClient không đảm bảo an toàn khi nhiều process cùng mở client
        trỏ vào cùng 1 thư mục — client đã mở sẵn có thể không thấy được thay đổi từ process khác,
        gây lỗi kiểu "Error creating hnsw segment reader: Nothing found on disk" dù dữ liệu trên
        disk hoàn toàn hợp lệ (client mới mở trong process khác đọc bình thường). Gọi lại hàm này
        tương đương "soft-restart" phần kết nối ChromaDB mà không cần restart cả server.
        """
        custom_logger.warning(
            f"[VectorDB] Reinitializing PersistentClient (stale segment handle recovery) | "
            f"path='{settings.CHROMA_PATH}'"
        )
        self.client = chromadb.PersistentClient(path=settings.CHROMA_PATH)

    def get_collection(self, name: str) -> Collection:
        """
        @desc Lấy collection hiện có hoặc tạo mới collection trong ChromaDB theo tên.
        Nếu metadata HNSW cũ bị conflict (vd: đổi embedding model), tự động xóa và tạo lại.
        @params name (str): Tên của collection cần lấy hoặc tạo mới
        @return Collection: Đối tượng collection ChromaDB tương ứng
        """
        try:
            return self.client.get_or_create_collection(name=name, metadata=_COLLECTION_METADATA)
        except Exception as e:
            if "hnsw" in str(e).lower() or "segment" in str(e).lower() or "parse" in str(e).lower():
                custom_logger.warning(
                    f"[VectorDB] collection '{name}' has stale HNSW metadata — resetting | error={e}"
                )
                try:
                    self.client.delete_collection(name=name)
                except Exception:
                    pass
                return self.client.create_collection(name=name, metadata=_COLLECTION_METADATA)
            raise

    def get_all_collections(self) -> dict[str, Collection]:
        """
        @desc Lấy tất cả các collection được định nghĩa sẵn trong hệ thống (overview, specs, reviews)
        @return dict[str, Collection]: Từ điển ánh xạ tên collection sang đối tượng Collection tương ứng
        """
        return {
            COLLECTION_OVERVIEW: self.get_collection(COLLECTION_OVERVIEW),
            COLLECTION_SPECS: self.get_collection(COLLECTION_SPECS),
            COLLECTION_REVIEWS: self.get_collection(COLLECTION_REVIEWS),
        }

    def upsert_documents(
        self,
        collection_name: str,
        ids: list,
        documents: list,
        metadatas: list = None,
        embeddings: list = None,
    ):
        """
        @desc Thêm mới hoặc cập nhật tài liệu trong collection, tự động tạo vector embedding nếu chưa được cung cấp
        @params collection_name (str): Tên collection cần thực hiện upsert
        @params ids (list): Danh sách ID tương ứng cho từng tài liệu
        @params documents (list): Danh sách nội dung văn bản của các tài liệu
        @params metadatas (list): Danh sách metadata đính kèm cho từng tài liệu (tuỳ chọn)
        @params embeddings (list): Danh sách vector embedding sẵn có; nếu None sẽ tự động tạo (tuỳ chọn)
        """
        custom_logger.info(f"[VectorDB] upsert | collection={collection_name} | count={len(ids)}")
        vecs = embeddings or self._embed(documents)
        self.get_collection(collection_name).upsert(
            ids=ids, documents=documents, embeddings=vecs, metadatas=metadatas
        )

    def add_documents(
        self,
        collection_name: str,
        ids: list,
        documents: list,
        metadatas: list = None,
        embeddings: list = None,
    ):
        """
        @desc Thêm mới các tài liệu vào collection, tự động tạo vector embedding nếu chưa được cung cấp
        @params collection_name (str): Tên collection cần thêm tài liệu
        @params ids (list): Danh sách ID tương ứng cho từng tài liệu
        @params documents (list): Danh sách nội dung văn bản của các tài liệu
        @params metadatas (list): Danh sách metadata đính kèm cho từng tài liệu (tuỳ chọn)
        @params embeddings (list): Danh sách vector embedding sẵn có; nếu None sẽ tự động tạo (tuỳ chọn)
        """
        custom_logger.info(f"[VectorDB] add | collection={collection_name} | count={len(ids)}")
        vecs = embeddings or self._embed(documents)
        self.get_collection(collection_name).add(
            ids=ids, documents=documents, embeddings=vecs, metadatas=metadatas
        )

    def update_documents(
        self,
        collection_name: str,
        ids: list,
        documents: list,
        metadatas: list = None,
        embeddings: list = None,
    ):
        """
        @desc Cập nhật nội dung và metadata của các tài liệu đã tồn tại trong collection, tự động tạo vector embedding nếu chưa cung cấp
        @params collection_name (str): Tên collection cần cập nhật tài liệu
        @params ids (list): Danh sách ID của các tài liệu cần cập nhật
        @params documents (list): Danh sách nội dung văn bản mới cho các tài liệu
        @params metadatas (list): Danh sách metadata mới đính kèm cho từng tài liệu (tuỳ chọn)
        @params embeddings (list): Danh sách vector embedding sẵn có; nếu None sẽ tự động tạo (tuỳ chọn)
        """
        custom_logger.info(f"[VectorDB] update | collection={collection_name} | count={len(ids)}")
        vecs = embeddings or self._embed(documents)
        self.get_collection(collection_name).update(
            ids=ids, documents=documents, embeddings=vecs, metadatas=metadatas
        )

    def delete_documents(
        self,
        collection_name: str,
        ids: list = None,
        filter_metadatas: dict = None,
    ):
        """
        @desc Xóa các tài liệu khỏi collection theo danh sách ID hoặc điều kiện lọc metadata
        @params collection_name (str): Tên collection cần xóa tài liệu
        @params ids (list): Danh sách ID của các tài liệu cần xóa (tuỳ chọn)
        @params filter_metadatas (dict): Điều kiện lọc theo metadata để xóa các tài liệu phù hợp (tuỳ chọn)
        """
        custom_logger.info(
            f"[VectorDB] delete | collection={collection_name} | "
            f"ids_count={len(ids) if ids else 0} | filter={filter_metadatas}"
        )
        self.get_collection(collection_name).delete(ids=ids, where=filter_metadatas)

    def query_similarity(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 5,
        filter_metadata: dict = None,
    ):
        """
        @desc Tìm kiếm các tài liệu tương đồng trong collection dựa trên vector embedding của văn bản truy vấn
        @params collection_name (str): Tên collection cần thực hiện tìm kiếm
        @params query_text (str): Văn bản truy vấn dùng để tìm kiếm tương đồng
        @params n_results (int): Số lượng kết quả trả về tối đa, mặc định là 5
        @params filter_metadata (dict): Điều kiện lọc theo metadata áp dụng khi tìm kiếm (tuỳ chọn)
        @return dict: Kết quả tìm kiếm chứa danh sách tài liệu, khoảng cách và metadata tương ứng
        """
        custom_logger.debug(
            f"[VectorDB] query_similarity | collection={collection_name} | n={n_results}"
        )
        from retrieval.embeddings import embed_query
        query_vec = embed_query(query_text)
        return self.get_collection(collection_name).query(
            query_embeddings=[query_vec],
            n_results=n_results,
            where=filter_metadata,
        )

    def count(self, collection_name: str) -> int:
        """
        @desc Đếm tổng số tài liệu hiện có trong một collection
        @params collection_name (str): Tên collection cần đếm số lượng tài liệu
        @return int: Tổng số tài liệu trong collection
        """
        count = self.get_collection(collection_name).count()
        custom_logger.debug(f"[VectorDB] count | collection={collection_name} | count={count}")
        return count

    @staticmethod
    def _embed(documents: list) -> list:
        """
        @desc Tạo vector embedding cho danh sách tài liệu văn bản bằng module embeddings
        @params documents (list): Danh sách văn bản cần tạo vector embedding
        @return list: Danh sách vector embedding tương ứng với từng tài liệu
        """
        from retrieval.embeddings import embed_documents
        return embed_documents(documents)
