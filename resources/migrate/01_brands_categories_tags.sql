-- ============================================================
-- SEED 01 — Brands · Categories · Tags
-- Engine  : MySQL 8.0+ / InnoDB / utf8mb4
-- Run     : first, after database.sql schema is applied
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
-- Brands
-- ============================================================
INSERT INTO Brands (id, name, slug, logo_url, description, is_active) VALUES
(1, 'Pancharm', 'pancharm',
 'https://cdn.pancharm.vn/brand/logo.png',
 'Pancharm — Thương hiệu trang sức đá phong thủy Gen Z hàng đầu Việt Nam. Chúng tôi kết hợp năng lượng đá quý thiên nhiên với thiết kế hiện đại, mang đến những món trang sức vừa mang ý nghĩa phong thủy sâu sắc, vừa đậm chất thời trang đương đại. Mỗi sản phẩm đều được tuyển chọn đá thiên nhiên chất lượng cao, chế tác bằng bạc 925 chuẩn.',
 TRUE);

-- ============================================================
-- Categories  (depth 0 = main, depth 1 = sub)
-- ============================================================
INSERT INTO Categories (id, name, slug, description, parent_id, depth_level, is_active) VALUES
-- depth 0 — main categories
(1,  'Vòng Tay',           'vong-tay',           'Vòng tay và lắc tay đá tự nhiên, bạc 925',          NULL, 0, TRUE),
(2,  'Dây Chuyền',         'day-chuyen',          'Dây chuyền mặt charm, choker, layer',                NULL, 0, TRUE),
(3,  'Nhẫn',               'nhan',                'Nhẫn đơn, nhẫn đôi đính đá quý',                    NULL, 0, TRUE),
(4,  'Bông Tai',           'bong-tai',            'Khuyên nụ, khuyên dài, ear cuff đính đá',            NULL, 0, TRUE),
(5,  'Lắc Chân',           'lac-chan',             'Lắc chân đá tự nhiên và bạc 925',                   NULL, 0, TRUE),
-- depth 1 — sub-categories
(6,  'Vòng Tay Bạc',       'vong-tay-bac',        'Vòng tay bạc 925 kết hợp đá quý cao cấp',           1,    1, TRUE),
(7,  'Vòng Tay Đá Chuỗi',  'vong-tay-da-chuoi',   'Vòng tay xâu chuỗi đá tự nhiên thuần túy',          1,    1, TRUE),
(8,  'Dây Chuyền Mặt',     'day-chuyen-mat',      'Dây chuyền có mặt charm / đá nổi bật',               2,    1, TRUE),
(9,  'Dây Chuyền Choker',  'day-chuyen-choker',   'Dây chuyền ôm sát cổ phong cách hiện đại',           2,    1, TRUE),
(10, 'Dây Chuyền Layer',   'day-chuyen-layer',    'Dây chuyền nhiều tầng thời trang',                   2,    1, TRUE),
(11, 'Nhẫn Đơn',           'nhan-don',            'Nhẫn thiết kế đơn chiếc độc đáo',                    3,    1, TRUE),
(12, 'Nhẫn Đôi',           'nhan-doi',            'Nhẫn đôi dành cho các cặp đôi',                      3,    1, TRUE),
(13, 'Khuyên Nụ',          'khuyen-nu',           'Bông tai dạng nụ thanh lịch, đeo hàng ngày',         4,    1, TRUE),
(14, 'Khuyên Dài',         'khuyen-dai',          'Bông tai thả dài quyến rũ, phù hợp sự kiện',         4,    1, TRUE),
(15, 'Ear Cuff',           'ear-cuff',            'Khuyên kẹp không cần xỏ lỗ tai',                    4,    1, TRUE);

-- ============================================================
-- Tags
-- ============================================================
INSERT INTO Tags (id, name, slug, tag_type) VALUES
-- occasion
(1,  'Sinh Nhật',          'sinh-nhat',           'occasion'),
(2,  'Kỷ Niệm',            'ky-niem',             'occasion'),
(3,  'Quà Tặng',           'qua-tang',            'occasion'),
(4,  'Năm Mới',            'nam-moi',             'occasion'),
(5,  'Lễ Tình Nhân',       'le-tinh-nhan',        'occasion'),
(6,  'Thi Cử',             'thi-cu',              'occasion'),
(7,  'Thăng Chức',         'thang-chuc',          'occasion'),
(8,  'Lễ 8/3',             'le-8-3',              'occasion'),
(9,  'Tiệc Tùng',          'tiec-tung',           'occasion'),
(10, 'Đính Hôn',           'dinh-hon',            'occasion'),
(11, 'Tự Thưởng',          'tu-thuong',           'occasion'),
(12, 'Khai Trương',        'khai-truong',         'occasion'),
(13, 'Tốt Nghiệp',         'tot-nghiep',          'occasion'),
(14, 'Lễ Giáng Sinh',      'le-giang-sinh',       'occasion'),
-- feng_shui
(15, 'Tình Duyên',         'tinh-duyen',          'feng_shui'),
(16, 'Tài Lộc',            'tai-loc',             'feng_shui'),
(17, 'Bình An',            'binh-an',             'feng_shui'),
(18, 'Sức Khỏe',           'suc-khoe',            'feng_shui'),
(19, 'Sự Nghiệp',          'su-nghiep',           'feng_shui'),
(20, 'Trừ Tà',             'tru-ta',              'feng_shui'),
(21, 'Trí Tuệ',            'tri-tue',             'feng_shui'),
(22, 'May Mắn',            'may-man',             'feng_shui'),
(23, 'Chữa Lành',          'chua-lanh',           'feng_shui'),
-- style
(24, 'Minimalist',         'minimalist',          'style'),
(25, 'Boho',               'boho',                'style'),
(26, 'Vintage',            'vintage',             'style'),
(27, 'Coquette',           'coquette',            'style'),
(28, 'Streetwear',         'streetwear',          'style'),
(29, 'Soft Luxe',          'soft-luxe',           'style'),
(30, 'Unisex',             'unisex',              'style'),
(31, 'Y2K',                'y2k',                 'style'),
-- product
(32, 'Bạc 925',            'bac-925',             'product'),
(33, 'Đá Tự Nhiên',        'da-tu-nhien',         'product'),
(34, 'Ngọc Trai',          'ngoc-trai',           'product'),
(35, 'Nhẫn Đôi',           'nhan-doi-tag',        'product'),
(36, 'Quà Cao Cấp',        'qua-cao-cap',         'product'),
(37, 'Mệnh Kim',           'menh-kim',            'product'),
(38, 'Mệnh Mộc',           'menh-moc',            'product'),
(39, 'Mệnh Thủy',          'menh-thuy',           'product'),
(40, 'Mệnh Hỏa',           'menh-hoa',            'product'),
(41, 'Mệnh Thổ',           'menh-tho',            'product');

SET FOREIGN_KEY_CHECKS = 1;
