import json
from app import app, db, Category, Vocabulary

# Dữ liệu mẫu khởi tạo gồm 50 từ vựng căn bản
data = [
    {"word": "Time", "pos": "noun", "pronunciation": "/taɪm/", "meaning": "Thời gian", "example": "Do you have time for a cup of coffee?"},
    {"word": "Year", "pos": "noun", "pronunciation": "/jɪər/", "meaning": "Năm", "example": "Happy new year!"},
    {"word": "People", "pos": "noun", "pronunciation": "/ˈpiː.pəl/", "meaning": "Mọi người, con người", "example": "Many people like to travel."},
    {"word": "Way", "pos": "noun", "pronunciation": "/weɪ/", "meaning": "Đường, cách thức", "example": "Can you show me the way to the station?"},
    {"word": "Day", "pos": "noun", "pronunciation": "/deɪ/", "meaning": "Ngày", "example": "It's a beautiful day."},
    {"word": "Man", "pos": "noun", "pronunciation": "/mæn/", "meaning": "Người đàn ông", "example": "He is a good man."},
    {"word": "Thing", "pos": "noun", "pronunciation": "/θɪŋ/", "meaning": "Vật, đồ vật", "example": "What is that thing?"},
    {"word": "Woman", "pos": "noun", "pronunciation": "/ˈwʊm.ən/", "meaning": "Người phụ nữ", "example": "She is a strong woman."},
    {"word": "Life", "pos": "noun", "pronunciation": "/laɪf/", "meaning": "Cuộc sống", "example": "Life is full of surprises."},
    {"word": "Child", "pos": "noun", "pronunciation": "/tʃaɪld/", "meaning": "Trẻ em", "example": "The child is playing with a toy."},
    {"word": "World", "pos": "noun", "pronunciation": "/wɜːld/", "meaning": "Thế giới", "example": "We live in a beautiful world."},
    {"word": "School", "pos": "noun", "pronunciation": "/skuːl/", "meaning": "Trường học", "example": "I go to school every day."},
    {"word": "State", "pos": "noun", "pronunciation": "/steɪt/", "meaning": "Tiểu bang, trạng thái", "example": "What state do you live in?"},
    {"word": "Family", "pos": "noun", "pronunciation": "/ˈfæm.əl.i/", "meaning": "Gia đình", "example": "My family is very important to me."},
    {"word": "Student", "pos": "noun", "pronunciation": "/ˈstjuː.dənt/", "meaning": "Học sinh", "example": "I am a student at the university."},
    {"word": "Group", "pos": "noun", "pronunciation": "/ɡruːp/", "meaning": "Nhóm", "example": "A group of friends went out for dinner."},
    {"word": "Country", "pos": "noun", "pronunciation": "/ˈkʌn.tri/", "meaning": "Đất nước", "example": "Vietnam is a beautiful country."},
    {"word": "Problem", "pos": "noun", "pronunciation": "/ˈprɒb.ləm/", "meaning": "Vấn đề", "example": "We need to solve this problem."},
    {"word": "Hand", "pos": "noun", "pronunciation": "/hænd/", "meaning": "Bàn tay", "example": "Raise your hand if you know the answer."},
    {"word": "Part", "pos": "noun", "pronunciation": "/pɑːt/", "meaning": "Phần", "example": "This is a key part of the project."},
    {"word": "Place", "pos": "noun", "pronunciation": "/pleɪs/", "meaning": "Nơi, địa điểm", "example": "This is a great place to relax."},
    {"word": "Case", "pos": "noun", "pronunciation": "/keɪs/", "meaning": "Trường hợp", "example": "In this case, we need to adapt."},
    {"word": "Week", "pos": "noun", "pronunciation": "/wiːk/", "meaning": "Tuần", "example": "I will see you next week."},
    {"word": "Company", "pos": "noun", "pronunciation": "/ˈkʌm.pə.ni/", "meaning": "Công ty", "example": "She works for a large company."},
    {"word": "System", "pos": "noun", "pronunciation": "/ˈsɪs.təm/", "meaning": "Hệ thống", "example": "The computer system is currently down."},
    {"word": "Right", "pos": "adjective", "pronunciation": "/raɪt/", "meaning": "Đúng, bên phải", "example": "You are absolutely right."},
    {"word": "Study", "pos": "verb", "pronunciation": "/ˈstʌd.i/", "meaning": "Học tập", "example": "I need to study for my exams."},
    {"word": "Book", "pos": "noun", "pronunciation": "/bʊk/", "meaning": "Quyển sách", "example": "I am reading a very interesting book."},
    {"word": "Eye", "pos": "noun", "pronunciation": "/aɪ/", "meaning": "Mắt", "example": "She has beautiful blue eyes."},
    {"word": "Job", "pos": "noun", "pronunciation": "/dʒɒb/", "meaning": "Công việc", "example": "He is looking for a new job."},
    {"word": "Word", "pos": "noun", "pronunciation": "/wɜːd/", "meaning": "Từ", "example": "What does this word mean?"},
    {"word": "Business", "pos": "noun", "pronunciation": "/ˈbɪz.nɪs/", "meaning": "Kinh doanh", "example": "They are in the restaurant business."},
    {"word": "Issue", "pos": "noun", "pronunciation": "/ˈɪʃ.uː/", "meaning": "Vấn đề (đang nhắc tới)", "example": "We have a major issue to resolve."},
    {"word": "Side", "pos": "noun", "pronunciation": "/saɪd/", "meaning": "Bên, mặt", "example": "Please look at both sides of the paper."},
    {"word": "Kind", "pos": "noun", "pronunciation": "/kaɪnd/", "meaning": "Loại, tốt bụng", "example": "That's a very kind thing to say."},
    {"word": "Head", "pos": "noun", "pronunciation": "/hed/", "meaning": "Cái đầu", "example": "He nodded his head in agreement."},
    {"word": "House", "pos": "noun", "pronunciation": "/haʊs/", "meaning": "Ngôi nhà", "example": "They bought a new house."},
    {"word": "Service", "pos": "noun", "pronunciation": "/ˈsɜː.vɪs/", "meaning": "Dịch vụ", "example": "The customer service here is excellent."},
    {"word": "Friend", "pos": "noun", "pronunciation": "/frend/", "meaning": "Bạn bè", "example": "She is my best friend."},
    {"word": "Father", "pos": "noun", "pronunciation": "/ˈfɑː.ðər/", "meaning": "Bố", "example": "My father is a teacher."},
    {"word": "Power", "pos": "noun", "pronunciation": "/paʊər/", "meaning": "Sức mạnh, quyền lực", "example": "Knowledge is power."},
    {"word": "Hour", "pos": "noun", "pronunciation": "/aʊər/", "meaning": "Giờ", "example": "I will be there in an hour."},
    {"word": "Game", "pos": "noun", "pronunciation": "/ɡeɪm/", "meaning": "Trò chơi", "example": "Do you want to play a game?"},
    {"word": "Line", "pos": "noun", "pronunciation": "/laɪn/", "meaning": "Dòng, đường kẻ", "example": "Please wait in line."},
    {"word": "End", "pos": "noun", "pronunciation": "/end/", "meaning": "Kết thúc", "example": "What happens at the end of the movie?"},
    {"word": "Member", "pos": "noun", "pronunciation": "/ˈmem.bər/", "meaning": "Thành viên", "example": "He is a member of the club."},
    {"word": "Law", "pos": "noun", "pronunciation": "/lɔː/", "meaning": "Pháp luật", "example": "We must obey the law."},
    {"word": "Car", "pos": "noun", "pronunciation": "/kɑːr/", "meaning": "Ô tô", "example": "He drives a fast car."},
    {"word": "City", "pos": "noun", "pronunciation": "/ˈsɪt.i/", "meaning": "Thành phố", "example": "I live in a big city."},
    {"word": "Community", "pos": "noun", "pronunciation": "/kəˈmjuː.nə.ti/", "meaning": "Cộng đồng", "example": "The local community is very supportive."}
]

def seed_database():
    with app.app_context():
        # Lấy category "1000 Từ Thông Dụng"
        cat = Category.query.filter_by(name="1000 Từ Thông Dụng").first()
        if not cat:
            cat = Category(name="1000 Từ Thông Dụng")
            db.session.add(cat)
            db.session.commit()
            
        added_count = 0
        for item in data:
            # Kiểm tra từ đã tồn tại chưa để tránh lặp
            exist = Vocabulary.query.filter_by(word=item['word'], category_id=cat.id).first()
            if not exist:
                vocab = Vocabulary(
                    word=item['word'],
                    pos=item['pos'],
                    pronunciation=item['pronunciation'],
                    meaning=item['meaning'],
                    example=item['example'],
                    category_id=cat.id
                )
                db.session.add(vocab)
                added_count += 1
                
        db.session.commit()
        print(f"✅ Đã chèn {added_count} từ vựng mới vào Category: {cat.name}!")

if __name__ == '__main__':
    seed_database()
