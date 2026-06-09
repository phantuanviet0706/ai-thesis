-- ================================================================
-- SEED DATA — PANCHARM RETAIL AI CONSULTATION PLATFORM
-- Source    : Sample data from gemini-code JSON files
-- Tables    : Categories, Products, ProductImages, ProductTags, ProductReviews
-- Usage     : mysql -u root -p pancharm_db < seed.sql
-- ================================================================
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ================================================================
-- BRANDS
-- ================================================================
INSERT INTO Brands (id, name, slug, logo_url, description, is_active) VALUES
(1, 'Pancharm', 'pancharm',
 'https://cdn.pancharm.vn/brand/logo.png',
 'Thương hiệu trang sức phong thủy đá quý thiên nhiên cao cấp tại Việt Nam. Mỗi sản phẩm được chế tác thủ công, kết hợp tinh hoa phong thủy học phương Đông và ngôn ngữ thiết kế hiện đại.',
 TRUE);

-- ================================================================
-- TAGS
-- ================================================================
INSERT INTO Tags (id, name, slug, tag_type) VALUES
-- feng_shui purpose
(1,  'Tài Lộc',       'tai-loc',       'feng_shui'),
(2,  'Tình Duyên',    'tinh-duyen',    'feng_shui'),
(3,  'Sức Khỏe',      'suc-khoe',      'feng_shui'),
(4,  'Bình An',       'binh-an',       'feng_shui'),
(5,  'Công Danh',     'cong-danh',     'feng_shui'),
(6,  'Trừ Tà',        'tru-ta',        'feng_shui'),
(7,  'Trí Tuệ',       'tri-tue',       'feng_shui'),
-- occasion
(8,  'Sinh Nhật',     'sinh-nhat',     'occasion'),
(9,  'Kỷ Niệm',       'ky-niem',       'occasion'),
(10, 'Năm Mới',       'nam-moi',       'occasion'),
(11, 'Tốt Nghiệp',    'tot-nghiep',    'occasion'),
(12, 'Khai Trương',   'khai-truong',   'occasion'),
(13, 'Tặng Bạn Gái',  'tang-ban-gai',  'occasion'),
(14, 'Tặng Bạn Trai', 'tang-ban-trai', 'occasion'),
(15, 'Tặng Mẹ',       'tang-me',       'occasion'),
(16, 'Lễ 8/3',        'le-8-3',        'occasion'),
(17, 'Lễ Tình Nhân',  'le-tinh-nhan',  'occasion'),
-- style
(18, 'Minimalist',    'minimalist',    'style'),
(19, 'Vintage',       'vintage',       'style'),
(20, 'Cá Tính',       'ca-tinh',       'style'),
(21, 'Boho',          'boho',          'style'),
(22, 'Luxury',        'luxury',        'style'),
(23, 'Unisex',        'unisex',        'style'),
(24, 'Basic',         'basic',         'style'),
(25, 'Gen Z',         'gen-z',         'style'),
(26, 'Cao Cấp',       'cao-cap',       'style');

-- ================================================================
-- CATEGORIES
-- ================================================================
INSERT INTO Categories (id, name, slug, description, parent_id, depth_level, is_active) VALUES
(1, 'Trang Sức Phong Thủy', 'trang-suc-phong-thuy',
 'Trang sức phong thủy đá quý thiên nhiên Pancharm — tài lộc, bình an, sức khỏe.',
 NULL, 0, TRUE),
(2, 'Vòng Tay Phong Thủy', 'vong-tay-phong-thuy',
 'Vòng tay và lắc tay đá quý phong thủy đa dạng mẫu mã, phù hợp mọi phong cách và mệnh số.',
 1, 1, TRUE),
(3, 'Dây Chuyền Phong Thủy', 'day-chuyen-phong-thuy',
 'Dây chuyền đá quý và ngọc trai phong thủy bạc 925, sang trọng và đầy ý nghĩa.',
 1, 1, TRUE),
(4, 'Nhẫn Phong Thủy', 'nhan-phong-thuy',
 'Nhẫn đá quý phong thủy mang lại vận may và bảo vệ người đeo.',
 1, 1, TRUE),
(5, 'Bông Tai Phong Thủy', 'bong-tai-phong-thuy',
 'Bông tai đá quý phong thủy tinh tế, tôn vẻ đẹp và mang lại may mắn.',
 1, 1, TRUE),
(6, 'Lắc Chân Phong Thủy', 'lac-chan-phong-thuy',
 'Lắc chân đá quý phong thủy mang bình an và may mắn trên mỗi bước đi.',
 1, 1, TRUE);

-- ================================================================
-- PRODUCTS (PC001-PC051)
-- ================================================================
INSERT INTO Products
  (id, name, slug, sku, description, short_description,
   category_id, brand_id, unit_price, sale_price,
   in_stock, stock_qty, attributes, status, embedding_status)
VALUES
(1, 'Vòng Tay Thạch Anh Hồng Classic Pancharm', 'vong-tay-thach-anh-hong-classic', 'PC001',
 'Chiếc vòng tay flagship của Pancharm — những hạt thạch anh hồng 8mm được lựa chọn kỹ lưỡng về độ trong và màu sắc, xâu trên dây đàn hồi cao cấp. Sắc hồng pastel dịu nhẹ tôn lên làn da và mang hào quang tình yêu bao phủ người đeo.',
 'Flagship vòng tay thạch anh hồng 8mm — tình yêu vô điều kiện, mở luân xa tim, thu hút nhân duyên.',
 2, 1, 1500000, 1350000, TRUE, 35,
 '{"stone":"Thạch Anh Hồng","element":"Thổ","chakra":"Tim","material":"dây đàn hồi cao cấp","bead_size_mm":8}',
 'active', 'pending'),

(2, 'Vòng Tay Đá Thạch Anh Hồng Minimalist Mix Charm Bạc', 'vong-tay-thach-anh-hong-minimalist-charm-bac', 'PC002',
 'Thiết kế vòng tay thạch anh hồng mang hơi hướng tối giản, thanh lịch nhưng không kém phần hiện đại. Sắc hồng pastel dịu nhẹ kết hợp cùng charm bạc nhỏ xinh giúp tôn lên vẻ nữ tính.',
 'Thạch anh hồng minimalist mix charm bạc — nữ tính, thu hút nhân duyên, cân bằng cảm xúc.',
 2, 1, 1250000, NULL, TRUE, 28,
 '{"stone":"Thạch Anh Hồng","element":"Thổ","chakra":"Tim","material":"bạc 925","bead_size_mm":6}',
 'active', 'pending'),

(3, 'Dây Chuyền Đá Mặt Trăng (Moonstone) Giọt Nước', 'day-chuyen-moonstone-giot-nuoc', 'PC003',
 'Mặt dây chuyền đá Moonstone cắt giác giọt nước tinh xảo, bắt sáng lấp lánh ở mọi góc nhìn, mang đậm phong cách soft luxe sang trọng mà vẫn trẻ trung.',
 'Moonstone giọt nước bắt sáng lấp lánh — xoa dịu tinh thần, tăng trực giác, thu hút may mắn.',
 3, 1, 1450000, NULL, TRUE, 22,
 '{"stone":"Moonstone","element":"Thủy","chakra":"Vương Miện","material":"bạc 925","chain_length_cm":42}',
 'active', 'pending'),

(4, 'Nhẫn Bạc Đính Đá Aquamarine Sóng Biển', 'nhan-bac-aquamarine-song-bien', 'PC004',
 'Chiếc nhẫn lấy cảm hứng từ những gợn sóng biển mềm mại, ôm trọn viên đá Aquamarine xanh trong vắt. Thiết kế trẻ trung, phá cách nhưng vẫn giữ được nét tinh tế.',
 'Aquamarine sóng biển — can đảm, thanh tẩy tâm trí, cải thiện giao tiếp và sự tự tin.',
 4, 1, 950000, NULL, TRUE, 18,
 '{"stone":"Aquamarine","element":"Thủy","chakra":"Cổ Họng","material":"bạc 925"}',
 'active', 'pending'),

(5, 'Lắc Tay Thạch Anh Tóc Vàng Bản Nhỏ Thanh Lịch', 'lac-tay-thach-anh-toc-vang-ban-nho', 'PC005',
 'Phiên bản lắc tay dạng xích bạc mix những viên thạch anh tóc vàng mini. Không quá hầm hố, thiết kế mang lại sự hiện đại và trendy cho những cô nàng công sở.',
 'Thạch anh tóc vàng xích bạc — thịnh vượng, thăng tiến sự nghiệp, thu hút tài lộc.',
 2, 1, 2100000, NULL, FALSE, 0,
 '{"stone":"Thạch Anh Tóc Vàng","element":"Kim","chakra":"Thái Dương","material":"bạc 925"}',
 'active', 'pending'),

(6, 'Bông Tai Hoa Đá Diopside Xanh Lục', 'bong-tai-hoa-diopside-xanh-luc', 'PC006',
 'Bông tai đính khuy nụ hình hoa cách điệu tinh xảo, điểm nhấn là viên ngọc Diopside xanh mướt nổi bật. Kiểu dáng nhỏ gọn, hợp thời trang.',
 'Diopside xanh lục hình hoa — chữa lành tâm hồn, thu hút vượng khí, bảo vệ sức khỏe.',
 5, 1, 850000, NULL, TRUE, 30,
 '{"stone":"Diopside","element":"Mộc","chakra":"Tim","material":"bạc 925"}',
 'active', 'pending'),

(7, 'Dây Chuyền Charm Đồng Điếu Ngọc Bích Khảm Bạc', 'day-chuyen-dong-dieu-ngoc-bich-kham-bac', 'PC007',
 'Đồng điếu ngọc bích thiên nhiên được bọc khung bạc cách điệu theo phong cách Gen Z năng động. Vừa mang hơi thở truyền thống vừa toát lên vẻ đẹp hiện đại.',
 'Đồng điếu ngọc bích khảm bạc — bình an, tài lộc, hóa giải xui xẻo đầy phong cách.',
 3, 1, 1650000, NULL, TRUE, 15,
 '{"stone":"Ngọc Bích","element":"Mộc","chakra":"Tim","material":"bạc 925","chain_length_cm":45}',
 'active', 'pending'),

(8, 'Vòng Tay Kẹo Ngọt Tourmaline Sắc Màu', 'vong-tay-tourmaline-sac-mau', 'PC008',
 'Sự kết hợp ngẫu hứng của những viên đá Tourmaline đa sắc tạo nên chiếc vòng tay rực rỡ, ngọt ngào như những viên kẹo. Dành riêng cho những tâm hồn tươi trẻ, thích sự phá cách.',
 'Tourmaline đa sắc rực rỡ — cân bằng năng lượng, tạo niềm vui, tăng sức sáng tạo.',
 2, 1, 1150000, NULL, TRUE, 20,
 '{"stone":"Tourmaline","element":"Hỏa","chakra":"Đan Điền","material":"dây dù cao cấp","bead_size_mm":8}',
 'active', 'pending'),

(9, 'Nhẫn Bạc Nam Tính Đính Đá Onyx Đen', 'nhan-bac-onyx-den-nam-tinh', 'PC009',
 'Mẫu nhẫn thiết kế tối giản, phom dáng vuông vắn mạnh mẽ với điểm nhấn là viên đá Onyx đen huyền bí. Phù hợp cho cả nam và nữ theo đuổi phong cách cá tính, quyền lực.',
 'Onyx đen huyền bí phom vuông — bảo vệ năng lượng tiêu cực, tăng sự tự tin và kiên định.',
 4, 1, 1350000, NULL, TRUE, 25,
 '{"stone":"Onyx","element":"Thủy","chakra":"Gốc","material":"bạc 925"}',
 'active', 'pending'),

(10, 'Vòng Chỉ Đỏ Mix Charm Cỏ 4 Lá Đá Citrine', 'vong-chi-do-mix-charm-co-4-la-citrine', 'PC010',
 'Sợi chỉ đỏ may mắn được tết thủ công tỉ mỉ, kết hợp cùng charm cỏ 4 lá chạm khắc từ đá thạch anh vàng (Citrine) tinh xảo. Một item nhỏ xinh, hiện đại mang đậm năng lượng tươi mới.',
 'Chỉ đỏ tết thủ công mix charm cỏ 4 lá Citrine — cầu may, hút tài lộc, bình an.',
 2, 1, 550000, NULL, TRUE, 50,
 '{"stone":"Citrine","element":"Thổ","chakra":"Thái Dương","material":"bạc 925"}',
 'active', 'pending');

-- ================================================================
-- PRODUCT IMAGES (3 images per product - first 10 products)
-- ================================================================
INSERT INTO ProductImages (id, product_id, url, alt_text, sort_order, is_primary) VALUES
-- Product 1
(1, 1, 'https://cdn.pancharm.vn/products/PC001/image-1.jpg', 'Vòng tay thạch anh hồng classic - góc chính diện', 0, TRUE),
(2, 1, 'https://cdn.pancharm.vn/products/PC001/image-2.jpg', 'Vòng tay thạch anh hồng classic - chi tiết hạt', 1, FALSE),
(3, 1, 'https://cdn.pancharm.vn/products/PC001/image-3.jpg', 'Vòng tay thạch anh hồng classic - mô phỏng lên tay', 2, FALSE),

-- Product 2
(4, 2, 'https://cdn.pancharm.vn/products/PC002/image-1.jpg', 'Vòng tay minimalist charm bạc - chính diện', 0, TRUE),
(5, 2, 'https://cdn.pancharm.vn/products/PC002/image-2.jpg', 'Detail charm bạc trên vòng', 1, FALSE),
(6, 2, 'https://cdn.pancharm.vn/products/PC002/image-3.jpg', 'Mô phỏng đeo lên tay', 2, FALSE),

-- Product 3
(7, 3, 'https://cdn.pancharm.vn/products/PC003/image-1.jpg', 'Dây chuyền moonstone - chính diện', 0, TRUE),
(8, 3, 'https://cdn.pancharm.vn/products/PC003/image-2.jpg', 'Đá moonstone chi tiết', 1, FALSE),
(9, 3, 'https://cdn.pancharm.vn/products/PC003/image-3.jpg', 'Mô phỏng thắc lên cổ', 2, FALSE),

-- Product 4
(10, 4, 'https://cdn.pancharm.vn/products/PC004/image-1.jpg', 'Nhẫn aquamarine - chính diện', 0, TRUE),
(11, 4, 'https://cdn.pancharm.vn/products/PC004/image-2.jpg', 'Chi tiết thiết kế sóng biển', 1, FALSE),
(12, 4, 'https://cdn.pancharm.vn/products/PC004/image-3.jpg', 'Mô phỏng lên tay', 2, FALSE),

-- Product 5
(13, 5, 'https://cdn.pancharm.vn/products/PC005/image-1.jpg', 'Lắc tay tóc vàng - chính diện', 0, TRUE),
(14, 5, 'https://cdn.pancharm.vn/products/PC005/image-2.jpg', 'Chi tiết tóc vàng', 1, FALSE),
(15, 5, 'https://cdn.pancharm.vn/products/PC005/image-3.jpg', 'Mô phỏng lên tay', 2, FALSE),

-- Product 6
(16, 6, 'https://cdn.pancharm.vn/products/PC006/image-1.jpg', 'Bông tai diopside - chính diện', 0, TRUE),
(17, 6, 'https://cdn.pancharm.vn/products/PC006/image-2.jpg', 'Chi tiết hoa diopside', 1, FALSE),
(18, 6, 'https://cdn.pancharm.vn/products/PC006/image-3.jpg', 'Mô phỏng đeo trên tai', 2, FALSE),

-- Product 7
(19, 7, 'https://cdn.pancharm.vn/products/PC007/image-1.jpg', 'Dây chuyền ngọc bích - chính diện', 0, TRUE),
(20, 7, 'https://cdn.pancharm.vn/products/PC007/image-2.jpg', 'Chi tiết đồng điếu ngọc bích', 1, FALSE),
(21, 7, 'https://cdn.pancharm.vn/products/PC007/image-3.jpg', 'Mô phỏng thắc lên cổ', 2, FALSE),

-- Product 8
(22, 8, 'https://cdn.pancharm.vn/products/PC008/image-1.jpg', 'Vòng tay tourmaline - chính diện', 0, TRUE),
(23, 8, 'https://cdn.pancharm.vn/products/PC008/image-2.jpg', 'Chi tiết đá tourmaline đa sắc', 1, FALSE),
(24, 8, 'https://cdn.pancharm.vn/products/PC008/image-3.jpg', 'Mô phỏng lên tay', 2, FALSE),

-- Product 9
(25, 9, 'https://cdn.pancharm.vn/products/PC009/image-1.jpg', 'Nhẫn onyx - chính diện', 0, TRUE),
(26, 9, 'https://cdn.pancharm.vn/products/PC009/image-2.jpg', 'Chi tiết thiết kế vuông', 1, FALSE),
(27, 9, 'https://cdn.pancharm.vn/products/PC009/image-3.jpg', 'Mô phỏng lên tay', 2, FALSE),

-- Product 10
(28, 10, 'https://cdn.pancharm.vn/products/PC010/image-1.jpg', 'Vòng chỉ đỏ - chính diện', 0, TRUE),
(29, 10, 'https://cdn.pancharm.vn/products/PC010/image-2.jpg', 'Chi tiết charm cỏ 4 lá citrine', 1, FALSE),
(30, 10, 'https://cdn.pancharm.vn/products/PC010/image-3.jpg', 'Mô phỏng lên tay', 2, FALSE);

-- ================================================================
-- PRODUCT TAGS (M:N relationships)
-- ================================================================
INSERT INTO ProductTags (product_id, tag_id) VALUES
-- Product 1 (Vòng tay thạch anh hồng classic)
(1, 2), (1, 13), (1, 18), (1, 9),

-- Product 2 (Vòng tay minimalist)
(2, 2), (2, 17), (2, 18), (2, 8),

-- Product 3 (Dây chuyền moonstone)
(3, 4), (3, 22), (3, 9), (3, 17),

-- Product 4 (Nhẫn aquamarine)
(4, 5), (4, 11), (4, 20), (4, 8),

-- Product 5 (Lắc tay tóc vàng)
(5, 1), (5, 5), (5, 12), (5, 22),

-- Product 6 (Bông tai diopside)
(6, 3), (6, 16), (6, 24), (6, 8),

-- Product 7 (Dây chuyền ngọc bích)
(7, 1), (7, 4), (7, 25), (7, 9),

-- Product 8 (Vòng tay tourmaline)
(8, 2), (8, 13), (8, 25), (8, 8),

-- Product 9 (Nhẫn onyx)
(9, 6), (9, 20), (9, 23), (9, 14),

-- Product 10 (Vòng chỉ đỏ)
(10, 1), (10, 10), (10, 24), (10, 8);

-- ================================================================
-- PRODUCT REVIEWS (From JSON sample data)
-- ================================================================
INSERT INTO ProductReviews
  (id, product_id, user_id, rating, title, body, is_verified_purchase, is_published, embedding_status)
VALUES
(1, 2, NULL, 5, 'Vòng tay xinh xỉu!',
 'Vòng tay ở ngoài màu hồng pastel rất xinh và cực kỳ tôn da. Đeo lên tay nhìn nhẹ nhàng, từ lúc đeo thấy tâm trạng vui vẻ hơn hẳn. Sẽ ủng hộ shop dài dài.',
 TRUE, TRUE, 'pending'),

(2, 3, NULL, 5, 'Đá moonstone sáng siêu đẹp',
 'Đá moonstone lên ánh xanh siêu đẹp, thiết kế basic dễ phối đồ đi làm lẫn đi chơi. Dây bạc sáng, không bị xỉn màu dù mình đeo tắm rửa hàng ngày.',
 TRUE, TRUE, 'pending'),

(3, 4, NULL, 5, 'Nhẫn lên tay cực xinh',
 'Form nhẫn lên tay rất xinh, viên đá xanh ngọc nhìn siêu mướt mắt. Cảm giác đeo rất thoải mái, bạn tư vấn size cũng chuẩn nữa.',
 TRUE, TRUE, 'pending'),

(4, 5, NULL, 5, 'Vòng tay sang xịn mịn',
 'Đá trong, tóc vàng ánh kim dày đặc nhìn cực kỳ sang. Mình đeo đi làm ai cũng khen, mới chốt được hợp đồng lớn không biết có phải do vía vòng không hehe.',
 TRUE, TRUE, 'pending'),

(5, 6, NULL, 5, 'Bông tai rất trẻ trung',
 'Màu xanh lá của viên đá ở ngoài đời nhìn rất nịnh mắt. Đeo khuyên chốt chắc chắn, thiết kế trẻ trung không bị già như mấy mẫu đá quý ngày xưa.',
 TRUE, TRUE, 'pending'),

(6, 7, NULL, 5, 'Dây chuyền chất lượng tuyệt vời',
 'Mua tặng bản thân dịp đầu năm, thiết kế đồng điếu nhỏ nhắn chứ không bị to thô. Ngọc sáng bóng, dây chuyền thanh mảnh cực ưng ý.',
 TRUE, TRUE, 'pending'),

(7, 8, NULL, 5, 'Vòng rực rỡ cực kỳ hợp mùa hè',
 'Vòng rực rỡ lắm, mang mùa hè cực kỳ hợp luôn. Đá sáng, mix màu rất khéo, năng động trẻ trung, rất hợp phong cách của mình.',
 TRUE, TRUE, 'pending'),

(8, 9, NULL, 5, 'Nhẫn ngầu cực kỳ',
 'Nhẫn lên tay cực ngầu, nam đeo hay nữ cá tính đeo đều đẹp. Chất bạc xước làm rất có gu, viên đá đen bóng loáng sang trọng.',
 TRUE, TRUE, 'pending'),

(9, 10, NULL, 5, 'Xinh xỉu quá rồi',
 'Xinh xỉu luôn! Dây đỏ chốt bạc rất dễ chỉnh size tay. Cỏ 4 lá bằng đá thật nên màu vàng lên trong vắt, giá lại quá hợp lý cho học sinh sinh viên.',
 TRUE, TRUE, 'pending'),

(10, 1, NULL, 5, 'Vòng tay flagship Pancharm',
 'Hạt đá thạch anh hồng cực kỳ sáng trong, màu hồng pastel rất nữ tính. Dây đàn hồi chịu đựng khá tốt, đeo được cả mùa không hỏng. Chắc chắn mua lại.',
 TRUE, TRUE, 'pending');

SET FOREIGN_KEY_CHECKS = 1;

