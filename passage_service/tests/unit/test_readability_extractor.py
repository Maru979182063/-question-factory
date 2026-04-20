from app.infra.crawl.extractors.readability_extractor import ReadabilityLikeExtractor


def test_cleanup_text_strips_title_and_byline_front_matter() -> None:
    extractor = ReadabilityLikeExtractor()

    cleaned = extractor._cleanup_text(
        "练好发展的“慢功夫”（评论员观察）\n\n陈凌 《人民日报》（2025年03月13日 第 05 版）\n\n把速度真正降下来，才能把发展的底盘打扎实。",
        title="练好发展的“慢功夫”（评论员观察）",
    )

    assert cleaned == "把速度真正降下来，才能把发展的底盘打扎实。"


def test_cleanup_text_strips_leading_photo_caption_front_matter() -> None:
    extractor = ReadabilityLikeExtractor()

    cleaned = extractor._cleanup_text(
        "图为科研人员在实验室观察样品。新华社记者 周牧摄\n\n中国日益成为“世界研发实验室”，背后是人才、产业和平台能力的共同支撑。",
        title="中国对全球科研人才释放“磁吸力”",
    )

    assert cleaned.startswith("中国日益成为“世界研发实验室”")
    assert "新华社记者 周牧摄" not in cleaned
