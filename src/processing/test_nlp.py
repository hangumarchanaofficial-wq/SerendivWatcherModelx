# Save this as test_nlp.py
from nlp_processor import NLPProcessor

processor = NLPProcessor()

# ========================================
# TEST 1: Negative article (Devastation)
# ========================================
print("="*60)
print("TEST 1: NEGATIVE ARTICLE (Devastation)")
print("="*60)

negative_text = """Rice fields destroyed by incessant rain and floods at Manampitiya, Gallalla in the Northcentral Province. Pic by Nimal Jayarathna

Hitad.lk has you covered with quality used or brand new cars for sale that are budget friendly yet reliable! Now is the time to sell your old ride for something more attractive to today's modern automotive market demands. Browse through our selection of affordable options now on Hitad.lk before deciding on what will work best for you!"""

result1 = processor.enrich_article("Devastation", negative_text)

if result1:
    print(f"Cleaned text: {result1['text_cleaned'][:200]}...")
    print(f"\nSentiment score: {result1['sentiment_score']}")
    print(f"Sentiment label: {result1['sentiment_label']}")
    print(f"Sector: {result1['sectors']}")
else:
    print("Article rejected (too short)")

# ========================================
# TEST 2: Positive article (Success story)
# ========================================
print("\n" + "="*60)
print("TEST 2: POSITIVE ARTICLE (Company Success)")
print("="*60)

positive_text = """Sri Lanka's leading technology company Dialog Axiata announced record-breaking quarterly profits today, reporting a remarkable 45% revenue growth compared to last year. The telecommunications giant attributed this outstanding performance to innovative digital solutions and exceptional customer satisfaction ratings.

CEO Supun Weerasinghe expressed his delight at the phenomenal results, stating that the company's investment in cutting-edge 5G infrastructure and artificial intelligence capabilities has positioned Dialog as the nation's premier technology provider. The stellar financial performance has exceeded all analyst expectations and demonstrates the company's brilliant strategic vision.

Industry experts praised Dialog's magnificent achievement, noting that the company's success creates tremendous opportunities for Sri Lankan technology sector growth. Shareholders celebrated the excellent news as stock prices surged to all-time highs, reflecting strong investor confidence in the company's promising future prospects.

The company plans to expand operations further, creating hundreds of high-quality jobs and fostering innovation across Sri Lanka's digital economy. This wonderful development signals a bright outlook for the nation's tech industry.

Subscribe to our newsletter for more updates. Follow us on social media."""

result2 = processor.enrich_article("Dialog Axiata Reports Record Profits and Outstanding Growth", positive_text)

if result2:
    print(f"Cleaned text: {result2['text_cleaned'][:300]}...")
    print(f"\nSentiment score: {result2['sentiment_score']}")
    print(f"Sentiment label: {result2['sentiment_label']}")
    print(f"Sector: {result2['sectors']}")
    print(f"Word count: {result2['word_count']}")
else:
    print("Article rejected (too short)")

# ========================================
# TEST 3: Another positive (Banking sector)
# ========================================
print("\n" + "="*60)
print("TEST 3: POSITIVE ARTICLE (Banking Achievement)")
print("="*60)

banking_positive = """Commercial Bank of Ceylon achieved extraordinary success at the prestigious Asia Banking Awards 2024, winning five major accolades including Best Retail Bank in Sri Lanka. The bank's impressive performance reflects its commitment to excellence and customer-centric innovation.

The bank's digital transformation initiatives have been hugely successful, with mobile banking users increasing by 60% and customer satisfaction scores reaching unprecedented levels. This remarkable achievement showcases the bank's leadership in financial technology adoption.

Managing Director Sanath Mahawithanage expressed immense pride in the team's dedication and the bank's outstanding contribution to Sri Lanka's financial sector. The awards recognize the bank's exceptional service quality, innovative products, and strong financial stability.

Analysts praised the bank's robust balance sheet and healthy profit margins, noting that these accomplishments position Commercial Bank as a powerhouse in the regional banking industry. The positive momentum is expected to continue throughout the year."""

result3 = processor.enrich_article("Commercial Bank Wins Top Banking Awards", banking_positive)

if result3:
    print(f"Cleaned text: {result3['text_cleaned'][:300]}...")
    print(f"\nSentiment score: {result3['sentiment_score']}")
    print(f"Sentiment label: {result3['sentiment_label']}")
    print(f"Sector: {result3['sectors']}")
else:
    print("Article rejected (too short)")

print("\n" + "="*60)
print("TESTING COMPLETE")
print("="*60)
