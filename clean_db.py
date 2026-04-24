from app import app, db, Vocabulary

def remove_duplicates():
    with app.app_context():
        all_vocab = Vocabulary.query.all()
        seen = set()
        duplicates_deleted = 0
        
        for v in all_vocab:
            # Identifier is a tuple of (Category_ID, lowercased word)
            word_lower = v.word.lower().strip()
            identifier = (v.category_id, word_lower)
            
            if identifier in seen:
                # Trùng lặp -> Xóa
                db.session.delete(v)
                duplicates_deleted += 1
            else:
                # Đánh dấu đã thấy
                seen.add(identifier)
                
        db.session.commit()
        print(f"SUCCESS:{duplicates_deleted}")

if __name__ == '__main__':
    remove_duplicates()
