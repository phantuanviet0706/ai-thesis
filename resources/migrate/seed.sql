-- ============================================================
-- SEED DATA — PANCHARM RETAIL AI CONSULTATION PLATFORM
-- Vietnamese feng shui jewelry (trang sức phong thủy)
-- ============================================================
-- Execution order respects FK dependencies.
-- Circular FK (Orders ↔ ConversationSessions) resolved via UPDATE at end.
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
-- [1] Brands
-- ============================================================
INSERT INTO Brands (id, name, slug, logo_url, description, is_active) VALUES
(1,  'Pancharm',             'pancharm',             'https://cdn.pancharm.vn/brands/pancharm-logo.png',       'Thương hiệu trang sức phong thủy hàng đầu Việt Nam, chuyên đá quý và vật phẩm phong thủy chính hãng.', TRUE),
(2,  'Kim Bảo Phong Thủy',   'kim-bao-phong-thuy',   'https://cdn.pancharm.vn/brands/kim-bao-logo.png',        'Chuyên trang sức kim loại quý kết hợp đá phong thủy, phong cách hiện đại.',                            TRUE),
(3,  'Ngọc Thanh Jewelry',   'ngoc-thanh-jewelry',   'https://cdn.pancharm.vn/brands/ngoc-thanh-logo.png',     'Thương hiệu trang sức ngọc bích và đá quý thiên nhiên cao cấp.',                                     TRUE),
(4,  'Hành Tinh Vàng',       'hanh-tinh-vang',       'https://cdn.pancharm.vn/brands/hanh-tinh-vang-logo.png', 'Trang sức vàng 18K và 24K với thiết kế phong thủy tinh tế.',                                         TRUE),
(5,  'Đá Quý Phương Nam',    'da-quy-phuong-nam',    'https://cdn.pancharm.vn/brands/phuong-nam-logo.png',     'Nhà cung cấp đá quý thiên nhiên từ miền Nam Việt Nam và các nước Đông Nam Á.',                        TRUE),
(6,  'Tinh Tú Craft',        'tinh-tu-craft',        'https://cdn.pancharm.vn/brands/tinh-tu-logo.png',        'Trang sức thủ công độc đáo, kết hợp nghệ thuật truyền thống và phong thủy hiện đại.',                TRUE),
(7,  'Phong Thủy Huyền Học', 'phong-thuy-huyen-hoc', 'https://cdn.pancharm.vn/brands/huyen-hoc-logo.png',      'Chuyên vật phẩm phong thủy cao cấp và tư vấn phong thủy chuyên sâu.',                                TRUE),
(8,  'Kim Cương Đỏ',         'kim-cuong-do',         'https://cdn.pancharm.vn/brands/kim-cuong-do-logo.png',   'Trang sức đá đỏ cao cấp: ruby, hồng ngọc, mã não đỏ phong thủy.',                                   TRUE),
(9,  'Bảo Ngọc Studio',      'bao-ngoc-studio',      'https://cdn.pancharm.vn/brands/bao-ngoc-logo.png',       'Xưởng chế tác trang sức ngọc trai và đá biển cao cấp tại Nha Trang.',                               TRUE),
(10, 'Thiên Mệnh Gems',      'thien-menh-gems',      'https://cdn.pancharm.vn/brands/thien-menh-logo.png',     'Đá quý nhập khẩu từ Myanmar, Sri Lanka và Ấn Độ, chứng nhận chất lượng GIA.',                       TRUE);

-- ============================================================
-- [2] Tags
-- ============================================================
INSERT INTO Tags (id, name, slug, tag_type) VALUES
(1,  'Phong Thủy',     'phong-thuy',     'feng_shui'),
(2,  'Mệnh Kim',       'menh-kim',       'feng_shui'),
(3,  'Mệnh Mộc',       'menh-moc',       'feng_shui'),
(4,  'Mệnh Thủy',      'menh-thuy',      'feng_shui'),
(5,  'Mệnh Hỏa',       'menh-hoa',       'feng_shui'),
(6,  'Mệnh Thổ',       'menh-tho',       'feng_shui'),
(7,  'Bán Chạy',       'ban-chay',       'promo'),
(8,  'Mới Ra Mắt',     'moi-ra-mat',     'promo'),
(9,  'Sinh Nhật',      'sinh-nhat',      'occasion'),
(10, 'Kỷ Niệm',        'ky-niem',        'occasion'),
(11, 'Vòng Tay',       'vong-tay',       'product'),
(12, 'Nhẫn',           'nhan',           'product'),
(13, 'Dây Chuyền',     'day-chuyen',     'product'),
(14, 'Hoa Tai',        'hoa-tai',        'product'),
(15, 'Đá Thiên Nhiên', 'da-thien-nhien', 'product');

-- ============================================================
-- [3] Categories
-- ============================================================
INSERT INTO Categories (id, name, slug, description, parent_id, depth_level, is_active) VALUES
-- depth 0 roots
(1,  'Trang Sức Phong Thủy',   'trang-suc-phong-thuy',  'Toàn bộ trang sức mang tính phong thủy từ đá quý thiên nhiên', NULL, 0, TRUE),
(2,  'Đá Quý & Khoáng Thạch',  'da-quy-khoang-thach',   'Đá quý thô và đã gia công phục vụ nhu cầu phong thủy',         NULL, 0, TRUE),
(3,  'Vật Phẩm Phong Thủy',    'vat-pham-phong-thuy',   'Vật phẩm trang trí và cầu may theo phong thủy học',            NULL, 0, TRUE),
-- depth 1 under Trang Sức Phong Thủy (id=1)
(4,  'Vòng Tay',   'vong-tay',   'Vòng đeo tay từ đá quý phong thủy',            1, 1, TRUE),
(5,  'Nhẫn',       'nhan',       'Nhẫn đá quý phong thủy các loại',              1, 1, TRUE),
(6,  'Dây Chuyền', 'day-chuyen', 'Dây chuyền và mặt dây chuyền phong thủy',      1, 1, TRUE),
(7,  'Hoa Tai',    'hoa-tai',    'Hoa tai, bông tai từ đá quý tự nhiên',         1, 1, TRUE),
(8,  'Lắc Tay',    'lac-tay',    'Lắc tay phong thủy cao cấp',                   1, 1, TRUE),
-- depth 1 under Đá Quý (id=2)
(9,  'Đá Thiên Nhiên', 'da-thien-nhien', 'Đá quý nguyên khối từ thiên nhiên',    2, 1, TRUE),
(10, 'Đá Gia Công',    'da-gia-cong',    'Đá quý đã được cắt mài và đánh bóng',  2, 1, TRUE),
-- depth 1 under Vật Phẩm (id=3)
(11, 'Tỳ Hưu',        'ty-huu',         'Tỳ Hưu phong thủy thu hút tài lộc',    3, 1, TRUE),
(12, 'Phật & Quan Âm', 'phat-quan-am',   'Tượng Phật và Quan Âm phong thủy',     3, 1, TRUE);

-- ============================================================
-- [4] Products
-- ============================================================
INSERT INTO Products (id, name, slug, sku, description, short_description, category_id, brand_id,
    unit_price, sale_price, in_stock, stock_qty, attributes, status, embedding_status) VALUES
(1,  'Vòng Tay Đá Mắt Hổ Vàng Phong Thủy', 'vong-tay-da-mat-ho-vang', 'PC-VT-001',
 'Vòng tay làm từ đá Mắt Hổ vàng thiên nhiên, hỗ trợ mệnh Kim và Thổ. Đá Mắt Hổ tăng cường tự tin, thu hút tài lộc và bảo vệ người đeo. Chọn lọc kỹ từ nguồn đá thiên nhiên Nam Phi.',
 'Vòng tay đá Mắt Hổ vàng, hợp mệnh Kim - Thổ, tăng tự tin và thu hút tài lộc.',
 4, 1, 850000.00, 720000.00, TRUE, 45,
 '{"material":"đá mắt hổ","element":"Kim, Thổ","size":"14mm","bead_count":14,"origin":"Nam Phi"}',
 'active', 'indexed'),

(2,  'Vòng Tay Thạch Anh Tím Amethyst Cao Cấp', 'vong-tay-thach-anh-tim-amethyst', 'PC-VT-002',
 'Vòng tay thạch anh tím (Amethyst) thiên nhiên chất lượng cao, hỗ trợ mệnh Thủy và Mộc. Amethyst mang lại bình yên, giảm căng thẳng, tăng trực giác. Nguồn gốc Brazil.',
 'Vòng thạch anh tím Amethyst Brazil, hợp mệnh Thủy - Mộc, mang bình yên và trực giác.',
 4, 1, 680000.00, NULL, TRUE, 38,
 '{"material":"thạch anh tím","element":"Thủy, Mộc","size":"10mm","bead_count":18,"origin":"Brazil"}',
 'active', 'indexed'),

(3,  'Vòng Tay Mã Não Đỏ Huyết Long', 'vong-tay-ma-nao-do-huyet-long', 'PC-VT-003',
 'Vòng tay Mã Não đỏ (Red Agate) cao cấp, màu đỏ đặc trưng của mệnh Hỏa. Mang lại năng lượng tích cực, sức mạnh, can đảm và bảo vệ mạnh mẽ. Thích hợp tuổi Ngọ, Dần, Tuất.',
 'Vòng Mã Não đỏ cao cấp, hợp mệnh Hỏa, tăng năng lượng và sức mạnh.',
 4, 8, 520000.00, 450000.00, TRUE, 62,
 '{"material":"mã não đỏ","element":"Hỏa","size":"12mm","compatible_zodiac":["Ngọ","Dần","Tuất"]}',
 'active', 'indexed'),

(4,  'Nhẫn Ngọc Bích Xanh Tự Nhiên', 'nhan-ngoc-bich-xanh-tu-nhien', 'PC-NH-001',
 'Nhẫn ngọc bích (Jade) xanh tự nhiên cấp A, thiết kế tinh tế viền vàng 18K. Ngọc bích biểu tượng may mắn, trường thọ và thịnh vượng. Phù hợp mệnh Mộc và Thủy.',
 'Nhẫn ngọc bích tự nhiên cấp A, viền vàng 18K, hợp mệnh Mộc - Thủy.',
 5, 3, 2800000.00, 2500000.00, TRUE, 15,
 '{"material":"ngọc bích","element":"Mộc, Thủy","metal":"vàng 18K","grade":"A","origin":"Myanmar"}',
 'active', 'indexed'),

(5,  'Dây Chuyền Mặt Tỳ Hưu Vàng 18K', 'day-chuyen-mat-ty-huu-vang-18k', 'PC-DC-001',
 'Dây chuyền mặt Tỳ Hưu vàng 18K, linh vật thu hút tài lộc và ngăn chặn vận xui. Tỳ Hưu ăn tiền nhưng không thải ra, tượng trưng tích lũy tài sản.',
 'Dây chuyền Tỳ Hưu vàng 18K, linh vật thu hút tài lộc và may mắn.',
 6, 4, 4500000.00, 3980000.00, TRUE, 20,
 '{"material":"vàng 18K","element":"Kim, Thổ","weight":"3.5g","length":"45cm","adjustable":true}',
 'active', 'indexed'),

(6,  'Vòng Tay Đá Đen Obsidian Bảo Vệ', 'vong-tay-da-den-obsidian-bao-ve', 'PC-VT-004',
 'Vòng tay đá Obsidian đen thiên nhiên, "lá chắn phong thủy" mạnh nhất. Hấp thụ năng lượng tiêu cực, bảo vệ khỏi tà khí và tăng trực giác. Thích hợp mệnh Thủy.',
 'Vòng Obsidian đen tự nhiên, lá chắn năng lượng, hợp mệnh Thủy.',
 4, 1, 380000.00, NULL, TRUE, 80,
 '{"material":"obsidian","element":"Thủy","size":"10mm","bead_count":20,"origin":"Mexico"}',
 'active', 'indexed'),

(7,  'Nhẫn Đá Lapis Lazuli Trí Tuệ', 'nhan-da-lapis-lazuli-tri-tue', 'PC-NH-002',
 'Nhẫn đá Lapis Lazuli xanh đậm với ánh vàng pyrite tự nhiên, đá của trí tuệ và sự thật. Phù hợp người làm việc trí óc, sinh viên cần sự minh mẫn.',
 'Nhẫn Lapis Lazuli xanh đậm, đá trí tuệ và sự thật, hợp mệnh Thủy.',
 5, 10, 1200000.00, 980000.00, TRUE, 28,
 '{"material":"lapis lazuli","element":"Thủy","origin":"Afghanistan","pyrite_content":"natural"}',
 'active', 'indexed'),

(8,  'Hoa Tai Ngọc Trai Nước Mặn Cao Cấp', 'hoa-tai-ngoc-trai-nuoc-man', 'PC-HT-001',
 'Hoa tai ngọc trai nước mặn Akoya Nhật Bản, màu trắng kem ánh hồng. Kích thước 7-8mm, độ bóng AAA, viền vàng 18K. Ngọc trai tượng trưng thuần khiết và may mắn.',
 'Hoa tai ngọc trai Akoya Nhật Bản AAA, viền vàng 18K, thanh lịch và sang trọng.',
 7, 9, 3200000.00, NULL, TRUE, 12,
 '{"material":"ngọc trai Akoya","element":"Thủy","size":"7-8mm","grade":"AAA","metal":"vàng 18K","origin":"Nhật Bản"}',
 'active', 'indexed'),

(9,  'Vòng Tay Thạch Anh Hồng Tình Yêu', 'vong-tay-thach-anh-hong-tinh-yeu', 'PC-VT-005',
 'Vòng tay thạch anh hồng (Rose Quartz) tự nhiên, đá của tình yêu và lòng trắc ẩn. Mở lòng, thu hút tình duyên và mang lại hài hòa trong các mối quan hệ. Thích hợp mệnh Kim và Thổ.',
 'Vòng thạch anh hồng Rose Quartz, đá tình yêu, hợp mệnh Kim - Thổ.',
 4, 1, 450000.00, 390000.00, TRUE, 55,
 '{"material":"thạch anh hồng","element":"Kim, Thổ","size":"8mm","bead_count":22,"origin":"Brazil"}',
 'active', 'indexed'),

(10, 'Dây Chuyền Thạch Anh Tím Mặt Trái Tim', 'day-chuyen-thach-anh-tim-mat-trai-tim', 'PC-DC-002',
 'Dây chuyền mặt thạch anh tím hình trái tim, chế tác tinh xảo viền bạc 925. Món quà ý nghĩa cho người thân yêu, mang ý nghĩa tình cảm sâu sắc.',
 'Dây chuyền mặt tim thạch anh tím, bạc 925, quà tặng ý nghĩa.',
 6, 1, 620000.00, 520000.00, TRUE, 40,
 '{"material":"thạch anh tím, bạc 925","element":"Thủy, Mộc","pendant_size":"2cm","chain_length":"45cm","gift_box":true}',
 'active', 'indexed'),

(11, 'Vòng Tay Vàng 18K Phong Thủy Hổ Phù', 'vong-tay-vang-18k-phong-thuy-ho-phu', 'PC-LT-001',
 'Lắc tay vàng 18K họa tiết Hổ Phù phong thủy, biểu tượng quyền lực và bảo vệ. Chế tác bởi nghệ nhân lành nghề, trọng lượng 5g, phù hợp mệnh Kim.',
 'Lắc tay vàng 18K họa tiết Hổ Phù, sang trọng và phong thủy.',
 8, 4, 8500000.00, 7800000.00, TRUE, 8,
 '{"material":"vàng 18K","element":"Kim","weight":"5g","size":"16-18cm adjustable","design":"Hổ Phù"}',
 'active', 'indexed'),

(12, 'Nhẫn Đá Ruby Phong Thủy Mệnh Hỏa', 'nhan-da-ruby-phong-thuy-menh-hoa', 'PC-NH-003',
 'Nhẫn đá Ruby đỏ tự nhiên Miến Điện 0.5ct, viền vàng 18K. Ruby là "vua của đá quý", mang sức mạnh, nhiệt huyết và may mắn cho mệnh Hỏa. Kèm chứng nhận GIA.',
 'Nhẫn Ruby đỏ Myanmar 0.5ct, vàng 18K, kèm chứng chỉ GIA.',
 5, 10, 12000000.00, NULL, TRUE, 5,
 '{"material":"ruby, vàng 18K","element":"Hỏa","carat":"0.5ct","color":"đỏ Pigeon Blood","certification":"GIA","origin":"Myanmar"}',
 'active', 'indexed');

-- ============================================================
-- [5] ProductImages
-- ============================================================
INSERT INTO ProductImages (id, product_id, url, alt_text, sort_order, is_primary) VALUES
(1,  1,  'https://cdn.pancharm.vn/products/pc-vt-001-main.jpg',   'Vòng tay đá Mắt Hổ vàng - ảnh chính',         0, TRUE),
(2,  1,  'https://cdn.pancharm.vn/products/pc-vt-001-detail.jpg', 'Vòng tay đá Mắt Hổ vàng - chi tiết',          1, FALSE),
(3,  2,  'https://cdn.pancharm.vn/products/pc-vt-002-main.jpg',   'Vòng thạch anh tím Amethyst - ảnh chính',     0, TRUE),
(4,  2,  'https://cdn.pancharm.vn/products/pc-vt-002-worn.jpg',   'Vòng thạch anh tím khi đeo tay',              1, FALSE),
(5,  3,  'https://cdn.pancharm.vn/products/pc-vt-003-main.jpg',   'Vòng Mã Não đỏ Huyết Long - ảnh chính',       0, TRUE),
(6,  3,  'https://cdn.pancharm.vn/products/pc-vt-003-set.jpg',    'Set vòng Mã Não đỏ kết hợp',                  1, FALSE),
(7,  4,  'https://cdn.pancharm.vn/products/pc-nh-001-main.jpg',   'Nhẫn ngọc bích xanh vàng 18K - ảnh chính',   0, TRUE),
(8,  4,  'https://cdn.pancharm.vn/products/pc-nh-001-close.jpg',  'Chi tiết ngọc bích cấp A',                    1, FALSE),
(9,  5,  'https://cdn.pancharm.vn/products/pc-dc-001-main.jpg',   'Dây chuyền Tỳ Hưu vàng 18K - ảnh chính',     0, TRUE),
(10, 5,  'https://cdn.pancharm.vn/products/pc-dc-001-worn.jpg',   'Dây chuyền Tỳ Hưu khi đeo',                  1, FALSE),
(11, 6,  'https://cdn.pancharm.vn/products/pc-vt-004-main.jpg',   'Vòng Obsidian đen bảo vệ - ảnh chính',        0, TRUE),
(12, 7,  'https://cdn.pancharm.vn/products/pc-nh-002-main.jpg',   'Nhẫn Lapis Lazuli xanh đậm - ảnh chính',     0, TRUE),
(13, 8,  'https://cdn.pancharm.vn/products/pc-ht-001-main.jpg',   'Hoa tai ngọc trai Akoya - ảnh chính',         0, TRUE),
(14, 8,  'https://cdn.pancharm.vn/products/pc-ht-001-pair.jpg',   'Đôi hoa tai ngọc trai nhìn cận',              1, FALSE),
(15, 9,  'https://cdn.pancharm.vn/products/pc-vt-005-main.jpg',   'Vòng thạch anh hồng - ảnh chính',             0, TRUE),
(16, 10, 'https://cdn.pancharm.vn/products/pc-dc-002-main.jpg',   'Dây chuyền mặt tim thạch anh tím - ảnh chính',0, TRUE),
(17, 10, 'https://cdn.pancharm.vn/products/pc-dc-002-box.jpg',    'Hộp quà dây chuyền thạch anh tím',            1, FALSE),
(18, 11, 'https://cdn.pancharm.vn/products/pc-lt-001-main.jpg',   'Lắc tay vàng 18K Hổ Phù - ảnh chính',        0, TRUE),
(19, 12, 'https://cdn.pancharm.vn/products/pc-nh-003-main.jpg',   'Nhẫn Ruby đỏ Myanmar vàng 18K - ảnh chính',  0, TRUE),
(20, 12, 'https://cdn.pancharm.vn/products/pc-nh-003-cert.jpg',   'Chứng chỉ GIA nhẫn Ruby',                     1, FALSE);

-- ============================================================
-- [6] ProductTags (M:N junction)
-- ============================================================
INSERT INTO ProductTags (product_id, tag_id) VALUES
(1, 1),(1, 2),(1, 6),(1, 7),(1, 11),
(2, 1),(2, 4),(2, 3),(2, 11),
(3, 1),(3, 5),(3, 7),(3, 11),
(4, 1),(4, 3),(4, 4),(4, 12),
(5, 1),(5, 2),(5, 6),(5, 13),
(6, 1),(6, 4),(6, 8),(6, 11),
(7, 1),(7, 4),(7, 12),
(8, 1),(8, 4),(8, 14),(8, 15),
(9, 1),(9, 2),(9, 9),(9, 11),
(10,1),(10,9),(10,10),(10,13),
(11,1),(11,2),(11,7),
(12,1),(12,5),(12,12),(12,15);

-- ============================================================
-- [7] Users
-- ============================================================
INSERT INTO Users (id, email, phone, password_hash, auth_provider, auth_provider_id, role, is_active, is_verified, last_login_at) VALUES
(1,  'nguyen.thi.lan@gmail.com',  '0901234567', '$2b$12$YZoRXXhashvalue00000001abc', 'local',    NULL,            'customer', TRUE,  TRUE,  '2026-06-10 08:30:00'),
(2,  'tran.van.nam@gmail.com',    '0912345678', '$2b$12$YZoRXXhashvalue00000002abc', 'local',    NULL,            'customer', TRUE,  TRUE,  '2026-06-12 14:20:00'),
(3,  'le.thi.hoa@gmail.com',      '0923456789', '$2b$12$YZoRXXhashvalue00000003abc', 'google',   'google_uid_003','customer', TRUE,  TRUE,  '2026-06-15 09:45:00'),
(4,  'pham.minh.tuan@gmail.com',  '0934567890', '$2b$12$YZoRXXhashvalue00000004abc', 'local',    NULL,            'customer', TRUE,  TRUE,  '2026-06-14 16:00:00'),
(5,  'hoang.thi.mai@yahoo.com',   '0945678901', '$2b$12$YZoRXXhashvalue00000005abc', 'local',    NULL,            'customer', TRUE,  FALSE, '2026-06-08 10:15:00'),
(6,  'huynh.van.binh@gmail.com',  '0956789012', '$2b$12$YZoRXXhashvalue00000006abc', 'facebook', 'fb_uid_006',   'customer', TRUE,  TRUE,  '2026-06-16 11:30:00'),
(7,  'phan.thi.thu@gmail.com',    '0967890123', '$2b$12$YZoRXXhashvalue00000007abc', 'local',    NULL,            'customer', TRUE,  TRUE,  '2026-06-13 13:00:00'),
(8,  'vu.anh.khoa@gmail.com',     '0978901234', '$2b$12$YZoRXXhashvalue00000008abc', 'zalo',     'zalo_uid_008', 'customer', TRUE,  TRUE,  '2026-06-11 15:45:00'),
(9,  'dang.thi.linh@gmail.com',   '0989012345', '$2b$12$YZoRXXhashvalue00000009abc', 'local',    NULL,            'customer', TRUE,  TRUE,  '2026-06-09 08:00:00'),
(10, 'ngo.minh.duc@gmail.com',    '0990123456', '$2b$12$YZoRXXhashvalue00000010abc', 'local',    NULL,            'customer', TRUE,  FALSE, '2026-06-07 17:20:00'),
(11, 'admin@pancharm.vn',         '0281234567', '$2b$12$YZoRXXhashvalueADMIN011abc', 'local',    NULL,            'admin',    TRUE,  TRUE,  '2026-06-17 07:00:00'),
(12, 'staff@pancharm.vn',         '0282345678', '$2b$12$YZoRXXhashvalueSTAFF012abc', 'local',    NULL,            'staff',    TRUE,  TRUE,  '2026-06-17 08:30:00');

-- ============================================================
-- [8] UserProfiles
-- ============================================================
INSERT INTO UserProfiles (id, user_id, display_name, avatar_url, date_of_birth, gender, zodiac_sign, preferences, total_orders, total_spent, loyalty_points, customer_segment) VALUES
(1,  1,  'Lan Nguyễn',     'https://cdn.pancharm.vn/avatars/u001.jpg', '1990-03-15', 'female', 'Song Ngư', '{"price_range":[500000,2000000],"fav_elements":["Thủy","Mộc"]}',        5, 3250000.00,  325,  'regular'),
(2,  2,  'Nam Trần',       'https://cdn.pancharm.vn/avatars/u002.jpg', '1988-07-22', 'male',   'Cự Giải',  '{"price_range":[1000000,5000000],"fav_elements":["Kim"]}',               3, 8200000.00,  820,  'vip'),
(3,  3,  'Hoa Lê',         'https://cdn.pancharm.vn/avatars/u003.jpg', '1995-11-08', 'female', 'Bọ Cạp',  '{"price_range":[300000,1500000],"fav_elements":["Hỏa"]}',               2, 970000.00,   97,   'new'),
(4,  4,  'Tuấn Phạm',      'https://cdn.pancharm.vn/avatars/u004.jpg', '1985-05-30', 'male',   'Song Tử',  '{"price_range":[2000000,15000000],"fav_elements":["Kim","Thổ"]}',       8, 45000000.00, 4500, 'vip'),
(5,  5,  'Mai Hoàng',      NULL,                                         '1992-09-12', 'female', 'Xử Nữ',   '{"price_range":[500000,3000000],"fav_elements":["Thổ"]}',               1, 680000.00,   68,   'new'),
(6,  6,  'Bình Huỳnh',     'https://cdn.pancharm.vn/avatars/u006.jpg', '1991-01-25', 'male',   'Bảo Bình', '{"price_range":[500000,2000000],"fav_elements":["Thủy","Kim"]}',         4, 2100000.00,  210,  'regular'),
(7,  7,  'Thu Phan',       'https://cdn.pancharm.vn/avatars/u007.jpg', '1993-06-17', 'female', 'Song Tử',  '{"price_range":[400000,1200000],"fav_elements":["Mộc"]}',               3, 1560000.00,  156,  'regular'),
(8,  8,  'Khoa Vũ',        'https://cdn.pancharm.vn/avatars/u008.jpg', '1987-12-03', 'male',   'Nhân Mã',  '{"price_range":[1000000,8000000],"fav_elements":["Hỏa","Kim"]}',        6, 18500000.00, 1850, 'vip'),
(9,  9,  'Linh Đặng',      'https://cdn.pancharm.vn/avatars/u009.jpg', '1996-04-20', 'female', 'Kim Ngưu', '{"price_range":[300000,1000000],"fav_elements":["Thổ"]}',               2, 870000.00,   87,   'new'),
(10, 10, 'Đức Ngô',        NULL,                                         '1983-08-11', 'male',   'Sư Tử',   '{"price_range":[5000000,20000000],"fav_elements":["Hỏa"]}',             0, 0.00,        0,    'churned'),
(11, 11, 'Admin Pancharm', 'https://cdn.pancharm.vn/avatars/admin.jpg','1985-01-01', 'male',   NULL,       '{}',                                                                    0, 0.00,        0,    'new'),
(12, 12, 'Staff Pancharm', 'https://cdn.pancharm.vn/avatars/staff.jpg','1992-06-15', 'female', NULL,       '{}',                                                                    0, 0.00,        0,    'new');

-- ============================================================
-- [9] UserAddresses
-- ============================================================
INSERT INTO UserAddresses (id, user_id, label, recipient_name, phone, address_line1, address_line2, ward, district, province, is_default) VALUES
(1,  1,  'Nhà',       'Nguyễn Thị Lan', '0901234567', '12 Nguyễn Trãi',              NULL,        'Phường Bến Thành',  'Quận 1',          'TP. Hồ Chí Minh', TRUE),
(2,  1,  'Văn phòng', 'Nguyễn Thị Lan', '0901234567', 'Tòa nhà Bitexco, Tầng 20',   'Phòng 2001','Phường Bến Nghé',   'Quận 1',          'TP. Hồ Chí Minh', FALSE),
(3,  2,  'Nhà',       'Trần Văn Nam',   '0912345678', '45 Lê Lợi',                  NULL,        'Phường Hội An',     'Quận Hải Châu',   'Đà Nẵng',         TRUE),
(4,  3,  'Nhà',       'Lê Thị Hoa',     '0923456789', '78 Trần Hưng Đạo',           NULL,        'Phường Phú Hội',    'Thành phố Huế',   'Thừa Thiên Huế',  TRUE),
(5,  4,  'Nhà',       'Phạm Minh Tuấn', '0934567890', '15 Hoàng Diệu',              'Căn hộ 5B', 'Phường Phước Ninh', 'Quận Hải Châu',   'Đà Nẵng',         TRUE),
(6,  4,  'Văn phòng', 'Phạm Minh Tuấn', '0934567890', '99 Bạch Đằng',              'Tầng 8',    'Phường Thạch Thang','Quận Hải Châu',   'Đà Nẵng',         FALSE),
(7,  5,  'Nhà',       'Hoàng Thị Mai',  '0945678901', '23 Điện Biên Phủ',           NULL,        'Phường Đa Kao',     'Quận 1',          'TP. Hồ Chí Minh', TRUE),
(8,  6,  'Nhà',       'Huỳnh Văn Bình', '0956789012', '67 Nguyễn Văn Cừ',           NULL,        'Phường An Hòa',     'Quận Ninh Kiều',  'Cần Thơ',         TRUE),
(9,  7,  'Nhà',       'Phan Thị Thu',   '0967890123', '34 Lạc Long Quân',           'Chung cư CT1','Phường 11',       'Quận 11',         'TP. Hồ Chí Minh', TRUE),
(10, 8,  'Nhà',       'Vũ Anh Khoa',    '0978901234', '56 Nguyễn Đình Chiểu',       NULL,        'Phường Đa Kao',     'Quận 1',          'TP. Hồ Chí Minh', TRUE),
(11, 9,  'Nhà',       'Đặng Thị Linh',  '0989012345', '89 Phan Đình Phùng',         NULL,        'Phường 1',          'Quận Phú Nhuận',  'TP. Hồ Chí Minh', TRUE),
(12, 10, 'Nhà',       'Ngô Minh Đức',   '0990123456', '101 Võ Văn Tần',             NULL,        'Phường 6',          'Quận 3',          'TP. Hồ Chí Minh', TRUE),
(13, 11, 'Văn phòng', 'Admin Pancharm', '0281234567', '250 Trần Não',               'Tầng 3',    'Phường Bình An',    'Quận 2',          'TP. Hồ Chí Minh', TRUE),
(14, 12, 'Văn phòng', 'Staff Pancharm', '0282345678', '250 Trần Não',               'Tầng 3',    'Phường Bình An',    'Quận 2',          'TP. Hồ Chí Minh', TRUE);

-- ============================================================
-- [10] Carts
-- ============================================================
INSERT INTO Carts (id, user_id, session_key, expires_at) VALUES
(1,  1,  NULL, '2026-07-17 00:00:00'),
(2,  2,  NULL, '2026-07-17 00:00:00'),
(3,  3,  NULL, '2026-07-17 00:00:00'),
(4,  4,  NULL, '2026-07-17 00:00:00'),
(5,  5,  NULL, '2026-07-17 00:00:00'),
(6,  6,  NULL, '2026-07-17 00:00:00'),
(7,  7,  NULL, '2026-07-17 00:00:00'),
(8,  8,  NULL, '2026-07-17 00:00:00'),
(9,  9,  NULL, '2026-07-17 00:00:00'),
(10, 10, NULL, '2026-07-17 00:00:00'),
(11, NULL, 'guest_sess_abc123def456', '2026-06-24 00:00:00'),
(12, NULL, 'guest_sess_xyz789ghi012', '2026-06-24 00:00:00');

-- ============================================================
-- [11] CartItems
-- ============================================================
INSERT INTO CartItems (id, cart_id, product_id, quantity) VALUES
(1,  1,  1,  1),
(2,  1,  9,  1),
(3,  2,  5,  1),
(4,  3,  3,  2),
(5,  4,  12, 1),
(6,  4,  11, 1),
(7,  5,  6,  1),
(8,  6,  2,  1),
(9,  7,  10, 1),
(10, 8,  4,  1),
(11, 9,  7,  1),
(12, 10, 8,  1),
(13, 11, 1,  1),
(14, 11, 3,  1),
(15, 12, 9,  2);

-- ============================================================
-- [12] ConversationSessions (linked_order_id = NULL, resolved via UPDATE later)
-- ============================================================
INSERT INTO ConversationSessions
    (id, thread_id, user_id, channel, status, final_psych_state, final_consult_strategy,
     total_turns, iteration_count, conversion_outcome, linked_order_id, started_at, last_active_at, ended_at)
VALUES
(1,  'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 1,  'web',      'completed', 'READY_TO_BUY', 'direct_recommendation', 6,  2, 'purchased',          NULL, '2026-06-01 09:00:00', '2026-06-01 09:25:00', '2026-06-01 09:25:00'),
(2,  'b2c3d4e5-f6a7-8901-bcde-f01234567891', 2,  'mobile',   'completed', 'READY_TO_BUY', 'upsell_premium',        8,  3, 'purchased',          NULL, '2026-06-02 14:00:00', '2026-06-02 14:40:00', '2026-06-02 14:40:00'),
(3,  'c3d4e5f6-a7b8-9012-cdef-012345678902', 3,  'facebook', 'completed', 'INTEREST',     'soft_recommendation',   4,  1, 'added_to_cart',      NULL, '2026-06-03 10:30:00', '2026-06-03 10:50:00', '2026-06-03 10:50:00'),
(4,  'd4e5f6a7-b8c9-0123-def0-123456789013', 4,  'web',      'completed', 'READY_TO_BUY', 'premium_showcase',      10, 4, 'purchased',          NULL, '2026-06-04 15:00:00', '2026-06-04 16:00:00', '2026-06-04 16:00:00'),
(5,  'e5f6a7b8-c9d0-1234-ef01-234567890124', 5,  'zalo',     'completed', 'HESITATION',   'reassurance_building',  5,  2, 'expressed_interest', NULL, '2026-06-05 11:00:00', '2026-06-05 11:30:00', '2026-06-05 11:30:00'),
(6,  'f6a7b8c9-d0e1-2345-f012-345678901235', 6,  'web',      'completed', 'READY_TO_BUY', 'direct_recommendation', 7,  2, 'purchased',          NULL, '2026-06-06 13:00:00', '2026-06-06 13:35:00', '2026-06-06 13:35:00'),
(7,  'a7b8c9d0-e1f2-3456-0123-456789012346', 7,  'mobile',   'completed', 'INTEREST',     'gift_framing',          6,  2, 'purchased',          NULL, '2026-06-07 16:00:00', '2026-06-07 16:30:00', '2026-06-07 16:30:00'),
(8,  'b8c9d0e1-f2a3-4567-1234-567890123457', 8,  'web',      'completed', 'READY_TO_BUY', 'premium_showcase',      9,  3, 'purchased',          NULL, '2026-06-08 10:00:00', '2026-06-08 10:45:00', '2026-06-08 10:45:00'),
(9,  'c9d0e1f2-a3b4-5678-2345-678901234568', 9,  'tiktok',   'completed', 'HESITATION',   'education_first',       4,  1, 'no_intent',          NULL, '2026-06-09 18:00:00', '2026-06-09 18:20:00', '2026-06-09 18:20:00'),
(10, 'd0e1f2a3-b4c5-6789-3456-789012345679', 10, 'web',      'abandoned', 'HESITATION',   NULL,                    2,  1, 'no_intent',          NULL, '2026-06-10 20:00:00', '2026-06-10 20:10:00', NULL),
(11, 'e1f2a3b4-c5d6-7890-4567-890123456780', 1,  'web',      'active',    NULL,            NULL,                    1,  0, 'no_intent',          NULL, '2026-06-17 08:00:00', '2026-06-17 08:05:00', NULL),
(12, 'f2a3b4c5-d6e7-8901-5678-901234567891', 6,  'mobile',   'completed', 'READY_TO_BUY', 'direct_recommendation', 5,  1, 'purchased',          NULL, '2026-06-11 09:00:00', '2026-06-11 09:25:00', '2026-06-11 09:25:00');

-- ============================================================
-- [13] Orders  (conversation_session_id references sessions above)
-- ============================================================
INSERT INTO Orders
    (id, order_code, user_id, shipping_address_id,
     subtotal, discount_amount, shipping_fee, total_amount,
     status, payment_status, shipping_method, tracking_number, notes,
     conversation_session_id, confirmed_at, shipped_at, delivered_at)
VALUES
(1,  'PC-20260601-0001', 1,  1,  1170000.00,  130000.00, 30000.00, 1070000.00, 'delivered',  'paid',   'GHN Express', 'GHN202606010001', NULL,                          1, '2026-06-01 10:00:00','2026-06-02 08:00:00','2026-06-03 15:00:00'),
(2,  'PC-20260602-0001', 2,  3,  4500000.00,  400000.00, 0.00,     4100000.00, 'delivered',  'paid',   'GHTK',        'GHTK202606020001','Gói quà tặng, đừng ghi giá', 2, '2026-06-02 15:00:00','2026-06-03 09:00:00','2026-06-04 14:00:00'),
(3,  'PC-20260603-0001', 3,  4,  520000.00,   0.00,      30000.00, 550000.00,  'confirmed',  'paid',   'ViettelPost', NULL,              NULL,                          3, '2026-06-03 11:00:00', NULL, NULL),
(4,  'PC-20260604-0001', 4,  5,  20500000.00, 1500000.00,0.00,     19000000.00,'delivered',  'paid',   'GHN Express', 'GHN202606040001', 'Hàng cao cấp, cẩn thận',     4, '2026-06-04 16:30:00','2026-06-05 10:00:00','2026-06-06 14:00:00'),
(5,  'PC-20260606-0001', 6,  8,  770000.00,   0.00,      30000.00, 800000.00,  'shipped',    'paid',   'GHN Express', 'GHN202606060001', NULL,                          6, '2026-06-06 14:00:00','2026-06-07 08:00:00', NULL),
(6,  'PC-20260607-0001', 7,  9,  520000.00,   50000.00,  30000.00, 500000.00,  'delivered',  'paid',   'ViettelPost', 'VTP202606070001', 'Quà sinh nhật em gái',       7, '2026-06-07 17:00:00','2026-06-08 09:00:00','2026-06-09 16:00:00'),
(7,  'PC-20260608-0001', 8,  10, 12000000.00, 0.00,      0.00,     12000000.00,'delivered',  'paid',   'GHN Express', 'GHN202606080001', NULL,                          8, '2026-06-08 11:00:00','2026-06-09 08:00:00','2026-06-10 14:00:00'),
(8,  'PC-20260611-0001', 6,  8,  390000.00,   0.00,      30000.00, 420000.00,  'processing', 'paid',   'GHN Express', NULL,              NULL,                          12,'2026-06-11 10:00:00', NULL, NULL),
(9,  'PC-20260612-0001', 1,  1,  8500000.00,  700000.00, 0.00,     7800000.00, 'pending',    'unpaid', NULL,          NULL,              NULL,                          NULL, NULL, NULL, NULL),
(10, 'PC-20260613-0001', 2,  3,  2800000.00,  280000.00, 0.00,     2520000.00, 'confirmed',  'paid',   'GHTK',        NULL,              NULL,                          NULL,'2026-06-13 10:00:00', NULL, NULL),
(11, 'PC-20260614-0001', 4,  5,  4500000.00,  0.00,      0.00,     4500000.00, 'delivered',  'paid',   'GHN Express', 'GHN202606140001', NULL,                          NULL,'2026-06-14 09:00:00','2026-06-15 08:00:00','2026-06-16 15:00:00'),
(12, 'PC-20260615-0001', 7,  9,  1200000.00,  120000.00, 30000.00, 1110000.00, 'shipped',    'paid',   'ViettelPost', 'VTP202606150001', NULL,                          NULL,'2026-06-15 14:00:00','2026-06-16 08:00:00', NULL);

-- ============================================================
-- [14] OrderItems
-- ============================================================
INSERT INTO OrderItems (id, order_id, product_id, product_name, product_sku, unit_price, quantity, total_price) VALUES
(1,  1,  1,  'Vòng Tay Đá Mắt Hổ Vàng Phong Thủy',       'PC-VT-001', 720000.00,  1, 720000.00),
(2,  1,  9,  'Vòng Tay Thạch Anh Hồng Tình Yêu',          'PC-VT-005', 390000.00,  1, 390000.00),
(3,  2,  5,  'Dây Chuyền Mặt Tỳ Hưu Vàng 18K',            'PC-DC-001', 3980000.00, 1, 3980000.00),
(4,  3,  3,  'Vòng Tay Mã Não Đỏ Huyết Long',             'PC-VT-003', 450000.00,  1, 450000.00),
(5,  4,  12, 'Nhẫn Đá Ruby Phong Thủy Mệnh Hỏa',          'PC-NH-003', 12000000.00,1, 12000000.00),
(6,  4,  11, 'Vòng Tay Vàng 18K Phong Thủy Hổ Phù',       'PC-LT-001', 7800000.00, 1, 7800000.00),
(7,  5,  6,  'Vòng Tay Đá Đen Obsidian Bảo Vệ',           'PC-VT-004', 380000.00,  1, 380000.00),
(8,  5,  9,  'Vòng Tay Thạch Anh Hồng Tình Yêu',          'PC-VT-005', 390000.00,  1, 390000.00),
(9,  6,  3,  'Vòng Tay Mã Não Đỏ Huyết Long',             'PC-VT-003', 450000.00,  1, 450000.00),
(10, 7,  12, 'Nhẫn Đá Ruby Phong Thủy Mệnh Hỏa',          'PC-NH-003', 12000000.00,1, 12000000.00),
(11, 8,  9,  'Vòng Tay Thạch Anh Hồng Tình Yêu',          'PC-VT-005', 390000.00,  1, 390000.00),
(12, 9,  11, 'Vòng Tay Vàng 18K Phong Thủy Hổ Phù',       'PC-LT-001', 7800000.00, 1, 7800000.00),
(13, 10, 4,  'Nhẫn Ngọc Bích Xanh Tự Nhiên',              'PC-NH-001', 2500000.00, 1, 2500000.00),
(14, 11, 5,  'Dây Chuyền Mặt Tỳ Hưu Vàng 18K',            'PC-DC-001', 3980000.00, 1, 3980000.00),
(15, 12, 7,  'Nhẫn Đá Lapis Lazuli Trí Tuệ',              'PC-NH-002', 980000.00,  1, 980000.00);

-- ============================================================
-- [15] Payments
-- ============================================================
INSERT INTO Payments (id, order_id, payment_method, transaction_id, amount, status, gateway_response, paid_at) VALUES
(1,  1,  'momo',          'MOMO2026060100001',  1070000.00,  'success', '{"result_code":0,"message":"Thành công"}',                         '2026-06-01 09:30:00'),
(2,  2,  'vnpay',         'VNPAY2026060200001', 4100000.00,  'success', '{"vnp_ResponseCode":"00","vnp_Message":"Giao dịch thành công"}',   '2026-06-02 14:10:00'),
(3,  3,  'bank_transfer', 'ACB2026060300001',   550000.00,   'success', '{"bank":"ACB","ref":"PC20260603"}',                                '2026-06-03 11:30:00'),
(4,  4,  'credit_card',   'VISA2026060400001',  19000000.00, 'success', '{"card_brand":"Visa","last4":"4242","status":"captured"}',         '2026-06-04 15:30:00'),
(5,  5,  'zalopay',       'ZPAY2026060600001',  800000.00,   'success', '{"return_code":1,"return_message":"success"}',                     '2026-06-06 13:10:00'),
(6,  6,  'momo',          'MOMO2026060700001',  500000.00,   'success', '{"result_code":0,"message":"Thành công"}',                         '2026-06-07 16:15:00'),
(7,  7,  'bank_transfer', 'VCB2026060800001',   12000000.00, 'success', '{"bank":"Vietcombank","ref":"PC20260608"}',                        '2026-06-08 10:30:00'),
(8,  8,  'momo',          'MOMO2026061100001',  420000.00,   'success', '{"result_code":0,"message":"Thành công"}',                         '2026-06-11 09:15:00'),
(9,  9,  'cod',            NULL,                7800000.00,  'pending', NULL,                                                               NULL),
(10, 10, 'vnpay',         'VNPAY2026061300001', 2520000.00,  'success', '{"vnp_ResponseCode":"00"}',                                        '2026-06-13 09:30:00'),
(11, 11, 'credit_card',   'MSTR2026061400001',  4500000.00,  'success', '{"card_brand":"Mastercard","last4":"5555","status":"captured"}',   '2026-06-14 08:45:00'),
(12, 12, 'zalopay',       'ZPAY2026061500001',  1110000.00,  'success', '{"return_code":1,"return_message":"success"}',                     '2026-06-15 13:30:00');

-- ============================================================
-- [16] ProductReviews
-- ============================================================
INSERT INTO ProductReviews (id, product_id, user_id, order_item_id, rating, title, body, is_verified_purchase, is_published, embedding_status) VALUES
(1,  1,  1, 1,  5, 'Đá đẹp, chất lượng tuyệt vời!',         'Vòng tay Mắt Hổ vàng rất đẹp, màu sắc tự nhiên và bóng mịn. Đeo vào thấy tự tin hơn hẳn. Đóng gói cẩn thận, giao nhanh. Sẽ ủng hộ Pancharm tiếp!',                          TRUE, TRUE, 'indexed'),
(2,  9,  1, 2,  5, 'Tuyệt vời, người yêu thích lắm',        'Mua tặng sinh nhật người yêu, cô ấy thích lắm. Màu hồng nhẹ nhàng, hạt đá đều. Pancharm tư vấn nhiệt tình về mệnh và phong thủy phù hợp.',                                  TRUE, TRUE, 'indexed'),
(3,  5,  2, 3,  5, 'Tỳ Hưu vàng đẳng cấp, xứng tiền',      'Dây chuyền Tỳ Hưu vàng 18K rất tinh xảo và sang trọng. Chatbot AI của Pancharm tư vấn phong thủy rất chính xác với tuổi của tôi.',                                            TRUE, TRUE, 'indexed'),
(4,  3,  3, 4,  4, 'Màu đẹp nhưng size hơi lớn',            'Vòng tay Mã Não đỏ màu đẹp lắm, đỏ đậm rất sang. Tuy nhiên size hơi rộng so với cổ tay nhỏ. Sẽ mua thêm loại nhỏ hơn lần sau.',                                              TRUE, TRUE, 'indexed'),
(5,  12, 4, 5,  5, 'Ruby đỏ đẹp tuyệt, có GIA đàng hoàng', 'Nhẫn Ruby rất đẹp, màu đỏ Pigeon Blood chuẩn. Kèm chứng chỉ GIA yên tâm chất lượng. Mua làm quà kỷ niệm 10 năm cho vợ.',                                                     TRUE, TRUE, 'indexed'),
(6,  11, 4, 6,  5, 'Lắc vàng Hổ Phù quá xịn',              'Lắc tay vàng 18K thật sự đẳng cấp. Thiết kế Hổ Phù tinh xảo, vàng sáng đẹp. Đeo vào cảm giác sang trọng và may mắn. Rất hài lòng!',                                         TRUE, TRUE, 'indexed'),
(7,  6,  6, 7,  4, 'Obsidian bảo vệ năng lượng hiệu quả',  'Vòng Obsidian đen đeo vào thấy cảm giác được bảo vệ. Màu đen bóng đẹp. Hơi cứng khi đeo lần đầu nhưng dần quen. Giao hàng nhanh.',                                            TRUE, TRUE, 'indexed'),
(8,  3,  7, 9,  5, 'Quà sinh nhật hoàn hảo',                'Mua tặng em gái sinh nhật. Em thích lắm vì phù hợp mệnh Hỏa. Pancharm tư vấn rất tận tâm về ý nghĩa phong thủy. Đóng gói như hộp quà rất đẹp.',                             TRUE, TRUE, 'indexed'),
(9,  12, 8, 10, 5, 'Ruby xuất sắc, đầu tư xứng đáng',      'Nhẫn Ruby Myanmar 0.5ct thật sự xuất sắc. AI của Pancharm tư vấn đúng ngũ hành Hỏa của mình. Sẽ giới thiệu bạn bè.',                                                          TRUE, TRUE, 'indexed'),
(10, 4,  2, 13, 5, 'Ngọc bích cấp A đúng nghĩa',           'Nhẫn ngọc bích Myanmar cấp A rất đẹp. Màu xanh trong và bóng. Viền vàng 18K tinh tế. Tặng sinh nhật vợ, nàng rất thích.',                                                     TRUE, TRUE, 'indexed'),
(11, 5,  4, 14, 4, 'Đẹp, giao hơi chậm một chút',          'Dây chuyền Tỳ Hưu vàng 18K đẹp và tinh xảo. Mặt Tỳ Hưu chạm khắc chi tiết. Chỉ tiếc giao hàng chậm hơn dự kiến 1 ngày.',                                                   TRUE, TRUE, 'indexed'),
(12, 7,  7, 15, 5, 'Lapis Lazuli rất đẹp và ý nghĩa',      'Nhẫn Lapis Lazuli màu xanh đậm với ánh vàng pyrite rất độc đáo. AI Pancharm giải thích ý nghĩa phong thủy rất chi tiết và thuyết phục.',                                      TRUE, TRUE, 'indexed');

-- ============================================================
-- [17] ConversationMessages
-- ============================================================
INSERT INTO ConversationMessages (id, session_id, turn_number, role, content, agent_name, latency_ms, token_count) VALUES
(1,  1, 1, 'user',      'Xin chào, tôi sinh năm 1990, mệnh Thủy. Tôi muốn mua vòng tay phong thủy hợp mệnh.', NULL, NULL, NULL),
(2,  1, 1, 'assistant', 'Chào chị Lan! Chị sinh năm 1990 mệnh Thủy rất hợp với đá Thạch anh tím và Obsidian. Chị có muốn tôi gợi ý sản phẩm phù hợp không?', 'synth_agent', 1850, 89),
(3,  1, 2, 'user',      'Tôi muốn xem vòng tay khoảng 500-800k, phù hợp để tặng bản thân.', NULL, NULL, NULL),
(4,  1, 2, 'assistant', 'Với ngân sách 500-800k, tôi gợi ý Vòng Tay Đá Mắt Hổ Vàng (720k) hoặc Thạch Anh Hồng (390k). Cả hai đều phù hợp mệnh Thủy của chị.', 'synth_agent', 2100, 112),
(5,  2, 1, 'user',      'Tôi cần mua quà tặng cao cấp cho vợ sinh nhật, ngân sách 3-5 triệu.', NULL, NULL, NULL),
(6,  2, 1, 'assistant', 'Chào anh! Với ngân sách 3-5 triệu cho sinh nhật, tôi gợi ý Dây Chuyền Tỳ Hưu Vàng 18K (3.98 triệu) - sang trọng và mang ý nghĩa tài lộc. Vợ anh sinh năm nào ạ?', 'synth_agent', 2050, 124),
(7,  4, 1, 'user',      'Tôi muốn mua đồ phong thủy cao cấp nhất, ngân sách không giới hạn, mệnh Hỏa.', NULL, NULL, NULL),
(8,  4, 1, 'assistant', 'Với mệnh Hỏa và yêu cầu cao cấp, tôi giới thiệu Nhẫn Ruby Myanmar (12 triệu, có GIA) và Lắc Tay Vàng 18K Hổ Phù (7.8 triệu). Ruby là đá vua của mệnh Hỏa!', 'synth_agent', 1920, 135),
(9,  5, 1, 'user',      'Tôi nghe nói đá phong thủy có tác dụng thật không? Tôi còn do dự lắm...', NULL, NULL, NULL),
(10, 5, 1, 'assistant', 'Đây là câu hỏi hay! Đá phong thủy kết hợp năng lượng khoáng vật tự nhiên với tâm lý học hành vi. Nhiều khách hàng của chúng tôi chia sẻ cảm giác tích cực hơn sau khi sử dụng.', 'synth_agent', 2400, 158),
(11, 6, 1, 'user',      'Mệnh Thủy tôi hợp với đá gì? Ngân sách 500-800k.', NULL, NULL, NULL),
(12, 6, 1, 'assistant', 'Mệnh Thủy hợp nhất với đá xanh/đen: Obsidian (380k), Thạch Anh Tím (680k). Với ngân sách 500-800k, Thạch Anh Tím là lựa chọn xuất sắc nhất!', 'synth_agent', 1780, 98),
(13, 7, 1, 'user',      'Tôi muốn mua quà sinh nhật cho em gái mệnh Hỏa, ngân sách 500k.', NULL, NULL, NULL),
(14, 7, 1, 'assistant', 'Mệnh Hỏa rất hợp Mã Não Đỏ! Vòng Tay Mã Não Đỏ Huyết Long (450k) là quà sinh nhật tuyệt vời, vừa đẹp vừa ý nghĩa phong thủy!', 'synth_agent', 1650, 87),
(15, 8, 1, 'user',      'Tôi muốn đầu tư nhẫn đá quý cao cấp có chứng chỉ GIA.', NULL, NULL, NULL),
(16, 8, 1, 'assistant', 'Hiểu rồi anh! Chúng tôi có Nhẫn Ruby Myanmar 0.5ct kèm chứng chỉ GIA (12 triệu). Ruby là vua đá quý, hợp đặc biệt mệnh Hỏa. Anh sinh năm nào ạ?', 'synth_agent', 2150, 119),
(17, 9, 1, 'user',      'Đá phong thủy có đắt không, tôi không chắc có nên mua không.', NULL, NULL, NULL),
(18, 9, 1, 'assistant', 'Chúng tôi có nhiều mức giá từ 380k đến hàng chục triệu. Chị có thể cho biết mệnh và ngân sách để tôi gợi ý phù hợp không?', 'synth_agent', 1600, 72),
(19, 11,1, 'user',      'Chào, tôi cần tư vấn vòng tay phong thủy.', NULL, NULL, NULL),
(20, 12,1, 'user',      'Mệnh Thủy, muốn mua vòng tay khoảng 400-500k.', NULL, NULL, NULL);

-- ============================================================
-- [18] PsychStateLogs
-- ============================================================
INSERT INTO PsychStateLogs (id, session_id, turn_number, psych_state, confidence_score, primary_concern, consult_strategy, raw_output) VALUES
(1,  1, 1, 'INTEREST',     0.720, 'Tìm sản phẩm hợp mệnh Thủy',          'education_first',       '{"state":"INTEREST","confidence":0.720,"signals":["hỏi mệnh","muốn mua"]}'),
(2,  1, 2, 'READY_TO_BUY', 0.890, NULL,                                   'direct_recommendation', '{"state":"READY_TO_BUY","confidence":0.890,"signals":["ngân sách rõ","tặng bản thân"]}'),
(3,  2, 1, 'INTEREST',     0.750, 'Quà tặng sinh nhật cho vợ',            'gift_framing',          '{"state":"INTEREST","confidence":0.750,"signals":["quà sinh nhật","ngân sách rõ"]}'),
(4,  2, 2, 'READY_TO_BUY', 0.920, NULL,                                   'upsell_premium',        '{"state":"READY_TO_BUY","confidence":0.920,"signals":["3-5tr","yêu cầu cao cấp"]}'),
(5,  4, 1, 'READY_TO_BUY', 0.980, NULL,                                   'premium_showcase',      '{"state":"READY_TO_BUY","confidence":0.980,"signals":["không giới hạn","chủ động hỏi cao cấp"]}'),
(6,  5, 1, 'HESITATION',   0.830, 'Nghi ngờ hiệu quả đá phong thủy',     'reassurance_building',  '{"state":"HESITATION","confidence":0.830,"signals":["do dự","đặt câu hỏi hiệu quả"]}'),
(7,  5, 2, 'INTEREST',     0.650, 'Muốn tìm hiểu thêm',                  'education_first',       '{"state":"INTEREST","confidence":0.650,"signals":["lắng nghe giải thích","hỏi thêm"]}'),
(8,  6, 1, 'READY_TO_BUY', 0.870, NULL,                                   'direct_recommendation', '{"state":"READY_TO_BUY","confidence":0.870,"signals":["biết mệnh","có ngân sách"]}'),
(9,  7, 1, 'INTEREST',     0.780, 'Quà sinh nhật em gái',                 'gift_framing',          '{"state":"INTEREST","confidence":0.780,"signals":["quà tặng","ngân sách nhỏ hợp lý"]}'),
(10, 8, 1, 'READY_TO_BUY', 0.950, NULL,                                   'premium_showcase',      '{"state":"READY_TO_BUY","confidence":0.950,"signals":["muốn đầu tư","yêu cầu GIA"]}'),
(11, 9, 1, 'HESITATION',   0.900, 'Không tin vào hiệu quả đá phong thủy','education_first',       '{"state":"HESITATION","confidence":0.900,"signals":["do dự","chưa chắc mua"]}'),
(12, 12,1, 'READY_TO_BUY', 0.860, NULL,                                   'direct_recommendation', '{"state":"READY_TO_BUY","confidence":0.860,"signals":["biết ngân sách","biết mệnh"]}');

-- ============================================================
-- [19] AgentPerformanceLogs
-- ============================================================
INSERT INTO AgentPerformanceLogs
    (id, session_id, turn_number, agent_name, latency_ms, input_tokens, output_tokens, retrieval_score, retrieved_product_ids, error_message)
VALUES
(1,  1, 1, 'psych_agent',  450,  320,  85,  NULL,   NULL,          NULL),
(2,  1, 1, 'kr_agent',     820,  480,  210, 0.8750, '[1,2,6,9]',   NULL),
(3,  1, 1, 'synth_agent',  580,  890,  145, NULL,   NULL,          NULL),
(4,  2, 1, 'psych_agent',  380,  290,  78,  NULL,   NULL,          NULL),
(5,  2, 1, 'kr_agent',     950,  520,  245, 0.9120, '[5,8,11]',    NULL),
(6,  2, 1, 'synth_agent',  720,  1050, 168, NULL,   NULL,          NULL),
(7,  4, 1, 'psych_agent',  320,  265,  71,  NULL,   NULL,          NULL),
(8,  4, 1, 'kr_agent',     1100, 580,  290, 0.9650, '[11,12]',     NULL),
(9,  4, 1, 'synth_agent',  500,  1120, 178, NULL,   NULL,          NULL),
(10, 5, 1, 'psych_agent',  520,  340,  92,  NULL,   NULL,          NULL),
(11, 5, 1, 'kr_agent',     780,  420,  185, 0.7200, '[6,2,1]',     NULL),
(12, 5, 1, 'synth_agent',  1100, 980,  225, NULL,   NULL,          NULL);

-- ============================================================
-- [20] APIKeys
-- ============================================================
INSERT INTO APIKeys (id, name, key_hash, key_prefix, owner_user_id, scopes, rate_limit_rpm, is_active, last_used_at, expires_at) VALUES
(1,  'Pancharm Web App Production',     'sha256_3e7f9ab12cd45ef678901abcdef234567890123456789abc01', 'pk_live_web1', 11, '["chat:read","chat:write","products:read"]',            500,  TRUE,  '2026-06-17 08:00:00', NULL),
(2,  'Pancharm Mobile App iOS',         'sha256_4f8a0bc23de56fg789012bcdfe345678901234567890bcd02', 'pk_live_ios2', 11, '["chat:read","chat:write","products:read"]',            300,  TRUE,  '2026-06-16 20:00:00', NULL),
(3,  'Pancharm Mobile App Android',     'sha256_5g9b1cd34ef67gh890123cdef0456789012345678901cde03', 'pk_live_and3', 11, '["chat:read","chat:write","products:read"]',            300,  TRUE,  '2026-06-15 12:00:00', NULL),
(4,  'Pancharm Facebook Messenger Bot', 'sha256_6h0c2de45fg78hi901234def01567890123456789012def04', 'pk_live_fb04', 11, '["chat:read","chat:write"]',                            200,  TRUE,  '2026-06-14 09:00:00', NULL),
(5,  'Pancharm Zalo OA Bot',            'sha256_7i1d3ef56gh89ij012345ef012678901234567890123ef005', 'pk_live_zl05', 11, '["chat:read","chat:write"]',                            200,  TRUE,  '2026-06-13 15:00:00', NULL),
(6,  'TikTok Shop Integration',         'sha256_8j2e4fg67hi90jk123456fg013789012345678901234fg006', 'pk_live_tt06', 11, '["products:read","orders:read"]',                       100,  TRUE,  '2026-06-12 11:00:00', '2026-12-31 23:59:59'),
(7,  'Analytics Dashboard Key',         'sha256_9k3f5gh78ij01kl234567gh014890123456789012345gh007', 'pk_live_an07', 12, '["analytics:read"]',                                    50,   TRUE,  '2026-06-10 08:00:00', NULL),
(8,  'Staging Environment Key',         'sha256_0l4g6hi89jk12lm345678hi015901234567890123456hi008', 'pk_test_st08', 11, '["chat:read","chat:write","products:read","orders:read"]',1000, TRUE,  '2026-06-09 16:00:00', '2026-09-30 23:59:59'),
(9,  'Partner API - Tiki Integration',  'sha256_1m5h7ij90kl23mn456789ij016012345678901234567ij009', 'pk_live_tk09', 11, '["products:read"]',                                     50,   FALSE, '2026-05-01 10:00:00', '2026-06-01 00:00:00'),
(10, 'Developer Testing Key',           'sha256_2n6i8jk01lm34no567890jk017123456789012345678jk010', 'pk_test_dv10', 12, '["chat:read","chat:write","products:read"]',            200,  TRUE,  '2026-06-17 07:45:00', '2026-07-31 23:59:59');

-- ============================================================
-- [21] SystemConfigs
-- ============================================================
INSERT INTO SystemConfigs (id, config_key, config_value, value_type, description, is_sensitive, updated_by) VALUES
(1,  'ai.model.default',              'claude-sonnet-4-6',      'string',  'Model Claude mặc định cho toàn bộ agent pipeline',                FALSE, 11),
(2,  'ai.model.psych_agent',          'claude-sonnet-4-6',      'string',  'Model cho Psych Agent phân tích tâm lý người dùng',               FALSE, 11),
(3,  'ai.model.kr_agent',             'claude-haiku-4-5',       'string',  'Model cho KR Agent tìm kiếm sản phẩm (ưu tiên tốc độ)',           FALSE, 11),
(4,  'ai.model.synth_agent',          'claude-opus-4-8',        'string',  'Model cho Synthesis Agent tổng hợp câu trả lời cuối cùng',        FALSE, 11),
(5,  'ai.max_tokens.default',         '2048',                   'integer', 'Số token tối đa mỗi lượt assistant',                             FALSE, 11),
(6,  'ai.max_iterations',             '5',                      'integer', 'Số vòng lặp tối đa của LangGraph orchestrator',                  FALSE, 11),
(7,  'ai.temperature.psych',          '0.3',                    'float',   'Temperature cho Psych Agent (thấp = nhất quán hơn)',              FALSE, 11),
(8,  'ai.temperature.synth',          '0.7',                    'float',   'Temperature cho Synthesis Agent',                                 FALSE, 11),
(9,  'chromadb.collection.products',  'pancharm_products_v2',   'string',  'Tên ChromaDB collection cho sản phẩm',                           FALSE, 11),
(10, 'chromadb.collection.reviews',   'pancharm_reviews_v1',    'string',  'Tên ChromaDB collection cho đánh giá sản phẩm',                  FALSE, 11),
(11, 'chromadb.top_k',                '5',                      'integer', 'Số kết quả tối đa trả về từ ChromaDB vector search',             FALSE, 11),
(12, 'payment.cod.enabled',           'true',                   'boolean', 'Bật/tắt thanh toán khi nhận hàng (COD)',                         FALSE, 11),
(13, 'shipping.free_threshold',       '2000000',                'integer', 'Giá trị đơn hàng tối thiểu miễn phí vận chuyển (VND)',           FALSE, 11),
(14, 'session.timeout_minutes',       '30',                     'integer', 'Thời gian timeout phiên chat không hoạt động (phút)',             FALSE, 11),
(15, 'feature.psych_agent.enabled',   'true',                   'boolean', 'Bật/tắt Psych Agent trong pipeline',                             FALSE, 11),
(16, 'cars.eval.enabled',             'true',                   'boolean', 'Bật/tắt thu thập dữ liệu đánh giá CARS framework',               FALSE, 11),
(17, 'redis.checkpointer.ttl_hours',  '24',                     'integer', 'TTL của LangGraph checkpoint trên Redis (giờ)',                   FALSE, 11),
(18, 'api.rate_limit.global_rpm',     '1000',                   'integer', 'Giới hạn request/phút toàn bộ API',                              FALSE, 11),
(19, 'anthropic.api_key',             '***MASKED***',           'string',  'Anthropic API Key (lưu an toàn trong vault, không log)',           TRUE,  11),
(20, 'promotion.discount.vip_rate',   '0.10',                   'float',   'Tỷ lệ giảm giá cho khách VIP (10%)',                             FALSE, 11);

-- ============================================================
-- [22] AuditLogs
-- ============================================================
INSERT INTO AuditLogs (id, actor_id, actor_type, action, resource_type, resource_id, old_value, new_value, ip_address, user_agent) VALUES
(1,  11,   'user',   'product.create',        'Products',             1,    NULL,                             '{"name":"Vòng Tay Đá Mắt Hổ Vàng","sku":"PC-VT-001","unit_price":850000}',    '118.68.1.10',   'Mozilla/5.0 (Windows NT 10.0)'),
(2,  11,   'user',   'product.update',        'Products',             1,    '{"sale_price":null}',            '{"sale_price":720000}',                                                       '118.68.1.10',   'Mozilla/5.0 (Windows NT 10.0)'),
(3,  1,    'user',   'order.create',          'Orders',               1,    NULL,                             '{"order_code":"PC-20260601-0001","total_amount":1070000}',                    '27.72.100.5',   'Mozilla/5.0 (iPhone; CPU iPhone OS 17)'),
(4,  2,    'user',   'order.create',          'Orders',               2,    NULL,                             '{"order_code":"PC-20260602-0001","total_amount":4100000}',                    '14.161.20.8',   'Mozilla/5.0 (Android 14)'),
(5,  11,   'user',   'order.status_update',   'Orders',               1,    '{"status":"pending"}',           '{"status":"delivered"}',                                                      '118.68.1.10',   'Mozilla/5.0 (Windows NT 10.0)'),
(6,  12,   'user',   'product.create',        'Products',             12,   NULL,                             '{"name":"Nhẫn Đá Ruby Phong Thủy Mệnh Hỏa","sku":"PC-NH-003","unit_price":12000000}', '118.68.1.11', 'Mozilla/5.0 (Macintosh; Intel Mac OS X)'),
(7,  NULL, 'system', 'session.timeout',       'ConversationSessions', 10,   '{"status":"active"}',            '{"status":"abandoned"}',                                                      NULL,            'system/scheduler'),
(8,  1,    'user',   'review.create',         'ProductReviews',       1,    NULL,                             '{"rating":5,"product_id":1}',                                                 '27.72.100.5',   'Mozilla/5.0 (iPhone)'),
(9,  11,   'user',   'config.update',         'SystemConfigs',        4,    '{"config_value":"claude-sonnet-4-6"}', '{"config_value":"claude-opus-4-8"}',                                   '118.68.1.10',   'Mozilla/5.0 (Windows NT 10.0)'),
(10, 4,    'user',   'order.create',          'Orders',               4,    NULL,                             '{"order_code":"PC-20260604-0001","total_amount":19000000}',                   '171.244.50.3',  'Mozilla/5.0 (Windows NT 10.0)'),
(11, NULL, 'system', 'embedding.batch_index', 'Products',             NULL, NULL,                             '{"indexed_count":12,"collection":"pancharm_products_v2"}',                   NULL,            'system/chromadb-sync'),
(12, 8,    'user',   'order.create',          'Orders',               7,    NULL,                             '{"order_code":"PC-20260608-0001","total_amount":12000000}',                   '42.118.200.15', 'Mozilla/5.0 (iPhone; CPU iPhone OS 17)');

-- ============================================================
-- [23] Resolve circular FK: set linked_order_id on sessions that resulted in a purchase
-- ============================================================
UPDATE ConversationSessions SET linked_order_id = 1 WHERE id = 1;
UPDATE ConversationSessions SET linked_order_id = 2 WHERE id = 2;
UPDATE ConversationSessions SET linked_order_id = 4 WHERE id = 4;
UPDATE ConversationSessions SET linked_order_id = 5 WHERE id = 6;
UPDATE ConversationSessions SET linked_order_id = 6 WHERE id = 7;
UPDATE ConversationSessions SET linked_order_id = 7 WHERE id = 8;
UPDATE ConversationSessions SET linked_order_id = 8 WHERE id = 12;

SET FOREIGN_KEY_CHECKS = 1;
