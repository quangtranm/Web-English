document.addEventListener('DOMContentLoaded', () => {

    /* ─── DOM refs ─────────────────────────────────────── */
    const flashcardSection      = document.getElementById('flashcard-container');
    const flashcardElement      = document.getElementById('flashcard');
    const innerCard             = document.getElementById('flashcard-inner');
    const loader                = document.getElementById('loader');
    const controls              = document.getElementById('controls');
    const tilesContainer        = document.getElementById('tiles-container');
    const tilesGrid             = document.getElementById('tiles-grid');
    const categoryActions       = document.getElementById('category-actions');
    const selectedCategoryName  = document.getElementById('selected-category-name');
    const vocabSection          = document.getElementById('vocab-section');
    const grammarSection        = document.getElementById('grammar-section');
    const grammarGrid           = document.getElementById('grammar-grid');
    const vocabHeader           = document.querySelector('.vocab-header');
    const statsRow              = document.getElementById('stats-row');
    const hubVocab              = document.getElementById('hub-vocab');
    const hubGrammar            = document.getElementById('hub-grammar');
    const hubContainer          = document.getElementById('hub-container');
    const quizContainer         = document.getElementById('quiz-container');
    const appContainer          = document.querySelector('.app-layout');
  
    /* ─── Flashcard elements ───────────────────────────── */
    const wordPos           = document.getElementById('word-pos');
    const englishWord       = document.getElementById('english-word');
    const wordPronunciation = document.getElementById('word-pronunciation');
    const vietnameseMeaning = document.getElementById('vietnamese-meaning');
    const exampleSentence   = document.getElementById('example-sentence');
  
    /* ─── Buttons ──────────────────────────────────────── */
    const btnSound          = document.getElementById('btn-sound');
    const btnPrev           = document.getElementById('btn-prev');
    const btnNext           = document.getElementById('btn-next');
    const btnBack           = document.getElementById('btn-back');
    const btnFlashcardHome  = document.getElementById('btn-flashcard-home');
    const btnBackHome       = document.getElementById('btn-back-home');
    const btnStudyFlashcard = document.getElementById('btn-study-flashcard');
    const btnStudyQuiz      = document.getElementById('btn-study-quiz');
    const currentIndexEl    = document.getElementById('current-index');
    const totalCountEl      = document.getElementById('total-count');
  
    /* ─── State ────────────────────────────────────────── */
    let vocabularyList    = [];
    let categoriesList    = [];
    let currentIndex      = 0;
    let selectedCategoryId = null;
    let activeSection     = null;
  
    /* ═══════════════════════════════════════════════════
       UTILS
       ═══════════════════════════════════════════════════ */
    function shuffleArray(arr) {
      const a = [...arr];
      for (let i = a.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [a[i], a[j]] = [a[j], a[i]];
      }
      return a;
    }
  
    function show(...els) { els.forEach(el => el && el.classList.remove('hidden')); }
    function hide(...els) { els.forEach(el => el && el.classList.add('hidden')); }
  
    function setSelectionLayout(isActive) {
      appContainer?.classList.toggle('selection-active', isActive);
    }
  
    /* ═══════════════════════════════════════════════════
       SPEECH
       ═══════════════════════════════════════════════════ */
    function speak(text) {
      if (!('speechSynthesis' in window)) return;
      const utt = new SpeechSynthesisUtterance(text);
      utt.lang = 'en-US';
      utt.rate = 0.9;
      utt.pitch = 1.0;
      const voices = window.speechSynthesis.getVoices();
      const preferred = voices.find(v => v.lang === 'en-US' && (v.name.includes('Google') || v.name.includes('Female')));
      if (preferred) utt.voice = preferred;
      window.speechSynthesis.speak(utt);
    }
    if (window.speechSynthesis.onvoiceschanged !== undefined) {
      window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
    }
  
    /* ═══════════════════════════════════════════════════
       CATEGORIES
       ═══════════════════════════════════════════════════ */
    function getCategoryIcon(name) {
      const n = name.toLowerCase();
      if (n.includes('thông dụng') || n.includes('1000')) return 'fa-star';
      if (n.includes('giao tiếp') || n.includes('communication')) return 'fa-comments';
      if (n.includes('oxford') || n.includes('3000')) return 'fa-book-open';
      if (n.includes('ielts'))  return 'fa-graduation-cap';
      if (n.includes('toeic'))  return 'fa-briefcase';
      return 'fa-folder';
    }
  
    async function loadCategories() {
      try {
        const res = await fetch('/api/categories');
        categoriesList = await res.json();
        const totalWords = categoriesList.reduce((s, c) => s + (c.count || 0), 0);
        document.getElementById('stat-cats').textContent = categoriesList.length;
        document.getElementById('stat-words').textContent = totalWords;
        hide(loader);
        renderCategoryTiles();
      } catch (e) { console.error('Error loading categories', e); }
    }
  
    function renderCategoryTiles() {
      tilesGrid.innerHTML = '';
      hide(loader);
      show(tilesGrid);
  
      categoriesList.forEach((cat, i) => {
        const icon = getCategoryIcon(cat.name);
        const progress = Math.min(100, (i * 13 + 20) % 70 + 10);
        const tile = document.createElement('div');
        tile.className = 'tile category-tile anim-up';
        tile.style.animationDelay = `${i * 0.06}s`;
        tile.innerHTML = `
          <div class="tile-header">
            <div class="tile-icon"><i class="fa-solid ${icon}"></i></div>
            <div class="tile-arrow"><i class="fa-solid fa-chevron-right"></i></div>
          </div>
          <div class="tile-info">
            <div class="tile-word">${cat.name}</div>
            <div class="tile-pos">${cat.count || 0} từ vựng</div>
          </div>
          <div class="tile-progress-container">
            <div class="tile-progress-bar" style="width:${progress}%"></div>
          </div>
        `;
        tile.addEventListener('click', () => selectCategory(cat));
        tilesGrid.appendChild(tile);
      });
    }
  
    /* ═══════════════════════════════════════════════════
       GRAMMAR TILES
       ═══════════════════════════════════════════════════ */
    async function renderGrammarTiles() {
      if (!grammarGrid) return;
      grammarGrid.innerHTML = '<div class="loader"><i class="fa-solid fa-spinner fa-spin"></i> Đang tải...</div>';
  
      const categories = [
        { id:'tenses',       name:'Các thì (Tenses)',           icon:'🕒', color:'#0D9488' },
        { id:'passive',      name:'Câu bị động (Passive)',       icon:'🔄', color:'#059669' },
        { id:'relative',     name:'Mệnh đề quan hệ',            icon:'🔗', color:'#14B8A6' },
        { id:'conditionals', name:'Câu điều kiện & Ước',        icon:'⚡', color:'#D97706' },
        { id:'reported',     name:'Trực tiếp & Gián tiếp',      icon:'💬', color:'#0891B2' },
        { id:'comparison',   name:'Cấu trúc so sánh',           icon:'⚖️', color:'#6366F1' },
      ];
  
      try {
        const res = await fetch('/api/questions');
        const questions = await res.json();
        const counts = {};
        questions.forEach(q => {
          if (q.topic) {
            const match = categories.find(c =>
              q.topic.toLowerCase().includes(c.id) ||
              q.topic.toLowerCase().includes(c.name.toLowerCase())
            );
            if (match) counts[match.id] = (counts[match.id] || 0) + 1;
          }
        });
  
        grammarGrid.innerHTML = '';
        categories.forEach((cat, idx) => {
          const count = counts[cat.id] || 0;
          const tile = document.createElement('div');
          tile.className = 'grammar-tile anim-up';
          tile.style.animationDelay = `${idx * 0.07}s`;
          tile.innerHTML = `
            <div>
              <div style="font-size:2rem;margin-bottom:.7rem">${cat.icon}</div>
              <div class="grammar-title">${cat.name}</div>
            </div>
            <div class="grammar-meta">
              <span class="grammar-tag" style="background:${cat.color}18;color:${cat.color}">Trắc nghiệm</span>
              <span style="color:${count > 0 ? 'var(--ink-2)' : 'var(--ink-5)'}">
                <i class="fa-solid fa-circle-question"></i>
                ${count > 0 ? `${count} câu hỏi` : 'Chưa có bài'}
              </span>
            </div>
          `;
          if (count > 0) {
            tile.addEventListener('click', () => {
              const p = new URLSearchParams({ topic: cat.name });
              window.location.href = `/quiz/take?${p}`;
            });
          } else {
            tile.style.opacity = '.6';
            tile.style.cursor = 'default';
          }
          grammarGrid.appendChild(tile);
        });
      } catch (e) {
        grammarGrid.innerHTML = '<p style="color:var(--red);padding:2rem">Lỗi tải dữ liệu.</p>';
      }
    }
  
    /* ═══════════════════════════════════════════════════
       NAVIGATION / SECTIONS
       ═══════════════════════════════════════════════════ */
    function resetToSectionTop(section) {
      selectedCategoryId = null;
      hide(categoryActions, flashcardSection, quizContainer, controls);
      show(hubContainer);
      if (section === 'vocab') {
        show(vocabHeader, statsRow, tilesContainer, tilesGrid);
        vocabSection.scrollIntoView({ behavior:'smooth', block:'start' });
      } else {
        grammarSection.scrollIntoView({ behavior:'smooth', block:'start' });
      }
      setSelectionLayout(false);
    }
  
    function switchSection(section) {
      if (activeSection === section) { resetToSectionTop(section); return; }
      activeSection = section;
  
      selectedCategoryId = null;
      hide(categoryActions, flashcardSection, quizContainer, controls);
      show(hubContainer);
  
      if (section === 'vocab') {
        hubVocab.classList.add('active');
        hubGrammar.classList.remove('active');
        show(vocabSection, vocabHeader, statsRow, tilesContainer, tilesGrid);
        hide(grammarSection);
        renderCategoryTiles();
        vocabSection.scrollIntoView({ behavior:'smooth', block:'start' });
      } else {
        hubGrammar.classList.add('active');
        hubVocab.classList.remove('active');
        show(grammarSection);
        hide(vocabSection, vocabHeader, statsRow);
        renderGrammarTiles();
        grammarSection.scrollIntoView({ behavior:'smooth', block:'start' });
      }
      setSelectionLayout(false);
    }
  
    hubVocab?.addEventListener('click',   () => switchSection('vocab'));
    hubGrammar?.addEventListener('click', () => switchSection('grammar'));
  
    function selectCategory(cat) {
      selectedCategoryId = cat.id;
      selectedCategoryName.textContent = cat.name;
      hide(vocabHeader, statsRow, tilesContainer);
      show(categoryActions);
      setSelectionLayout(true);
    }
  
    /* ═══════════════════════════════════════════════════
       VOCABULARY FETCH
       ═══════════════════════════════════════════════════ */
    async function fetchVocabulary(categoryId = '') {
      show(loader);
      loader.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang tải dữ liệu...';
      hide(tilesGrid);
      try {
        const url = categoryId ? `/api/vocabulary?category_id=${categoryId}` : '/api/vocabulary';
        const res = await fetch(url);
        vocabularyList = await res.json();
        if (vocabularyList.length > 0) {
          currentIndex = 0;
          hide(loader);
          return true;
        }
        loader.innerHTML = 'Không có từ vựng trong chủ đề này.';
        return false;
      } catch (err) {
        console.error('Failed to load vocabulary:', err);
        loader.innerHTML = 'Lỗi tải dữ liệu.';
        return false;
      }
    }
  
    /* ═══════════════════════════════════════════════════
       FLASHCARD MODE
       ═══════════════════════════════════════════════════ */
    function loadCard(index) {
      innerCard.parentElement.classList.remove('flipped');
      setTimeout(() => {
        const w = vocabularyList[index];
        if (!w) return;
        wordPos.textContent          = w.pos || 'N/A';
        englishWord.textContent      = w.word;
        wordPronunciation.textContent = w.pronunciation || '';
        vietnameseMeaning.textContent = w.meaning;
        exampleSentence.textContent  = w.example || '';
        currentIndexEl.textContent   = index + 1;
        btnPrev.disabled = index === 0;
        btnNext.disabled = index === vocabularyList.length - 1;
      }, 150);
    }
  
    function switchToFlashcardMode() {
      vocabularyList = shuffleArray(vocabularyList);
      currentIndex = 0;
      hide(categoryActions, tilesContainer, quizContainer, vocabHeader, statsRow, hubContainer);
      show(flashcardSection, controls);
      totalCountEl.textContent = vocabularyList.length;
      loadCard(0);
      setSelectionLayout(true);
    }
  
    flashcardElement.addEventListener('click', e => {
      if (e.target.closest('button')) return;
      flashcardElement.classList.toggle('flipped');
    });
    btnNext.addEventListener('click', () => { if (currentIndex < vocabularyList.length - 1) loadCard(++currentIndex); });
    btnPrev.addEventListener('click', () => { if (currentIndex > 0) loadCard(--currentIndex); });
  
    btnStudyFlashcard.addEventListener('click', async () => {
      if (!selectedCategoryId) return;
      hide(categoryActions);
      show(tilesContainer);
      const ok = await fetchVocabulary(selectedCategoryId);
      ok ? switchToFlashcardMode() : show(categoryActions);
    });
  
    btnSound.addEventListener('click', e => {
      e.stopPropagation();
      speak(englishWord.textContent);
      btnSound.style.transform = 'scale(.88)';
      setTimeout(() => btnSound.style.transform = '', 160);
    });
  
    /* ─── Navigation back ──────────────────────────────── */
    function goBackToCategories() {
      hide(flashcardSection, controls, quizContainer);
      show(categoryActions, vocabHeader, statsRow, hubContainer);
      setSelectionLayout(false);
    }
    function goBackHome() {
      hide(flashcardSection, controls, categoryActions, quizContainer);
      show(vocabHeader, statsRow, hubContainer, tilesContainer, tilesGrid);
      selectedCategoryId = null;
      setSelectionLayout(false);
    }
  
    btnBack.addEventListener('click',         e => { e.stopPropagation(); goBackToCategories(); });
    btnFlashcardHome.addEventListener('click', e => { e.stopPropagation(); goBackHome(); });
    btnBackHome?.addEventListener('click',    () => goBackHome());
  
    /* ─── Keyboard shortcuts ───────────────────────────── */
    document.addEventListener('keydown', e => {
      if (e.key === 'ArrowRight' && !btnNext.disabled) btnNext.click();
      else if (e.key === 'ArrowLeft' && !btnPrev.disabled) btnPrev.click();
      else if ([' ', 'ArrowUp', 'ArrowDown'].includes(e.key)) {
        e.preventDefault();
        if (!flashcardSection.classList.contains('hidden')) flashcardElement.classList.toggle('flipped');
      }
    });
  
    /* ═══════════════════════════════════════════════════
       QUIZ MODE
       ═══════════════════════════════════════════════════ */
    const quizWord        = document.getElementById('quiz-word');
    const quizWordPos     = document.getElementById('quiz-word-pos');
    const quizPronunciation = document.getElementById('quiz-pronunciation');
    const quizOptions     = document.getElementById('quiz-options');
    const quizFeedback    = document.getElementById('quiz-feedback');
    const feedbackText    = document.getElementById('feedback-text');
    const quizNextBtn     = document.getElementById('quiz-next-btn');
    const quizProgressText = document.getElementById('quiz-progress-text');
    const backToHomeBtn   = document.getElementById('back-to-home-btn');
    const btnQuizBack     = document.getElementById('btn-quiz-back');
    const scoreEl         = document.getElementById('score');
    const btnQuizSound    = document.getElementById('btn-quiz-sound');
  
    let quizScore         = 0;
    let quizIndex         = 0;
    let quizQuestionList  = [];
    let isAnswered        = false;
    let retryCount        = 0;
  
    function switchToQuizMode() {
      hide(categoryActions, tilesContainer, flashcardSection, controls, vocabHeader, statsRow, hubContainer);
      show(quizContainer);
      startQuiz();
      setSelectionLayout(true);
    }
  
    btnStudyQuiz.addEventListener('click', async () => {
      if (!selectedCategoryId) return;
      hide(categoryActions);
      show(tilesContainer);
      const ok = await fetchVocabulary(selectedCategoryId);
      ok ? switchToQuizMode() : show(categoryActions);
    });
  
    function startQuiz() {
      quizScore = 0;
      quizIndex = 0;
      scoreEl.textContent = 0;
      quizQuestionList = shuffleArray([...vocabularyList]);
      document.getElementById('quiz-results-screen')?.remove();
      const quizCard    = quizContainer.querySelector('.quiz-card');
      const quizHeader  = quizContainer.querySelector('.quiz-header');
      const quizProgress = quizContainer.querySelector('.quiz-progress');
      show(quizCard, quizHeader, quizProgress);
      loadQuizQuestion();
    }
  
    function generateQuizOptions(correct) {
      let wrongs = [...new Set(
        vocabularyList.filter(w => w.id !== correct.id).map(w => w.meaning)
      )];
      if (wrongs.length < 3) {
        const fallbacks = ['Sự tình cờ, may mắn','Hạnh phúc','Thông minh','Quan trọng','Khó khăn','Thú vị'];
        fallbacks.forEach(m => {
          if (m !== correct.meaning && !wrongs.includes(m)) wrongs.push(m);
        });
      }
      return shuffleArray([...shuffleArray(wrongs).slice(0,3), correct.meaning]);
    }
  
    function loadQuizQuestion() {
      if (quizIndex >= quizQuestionList.length) { endQuiz(); return; }
      isAnswered = false;
      retryCount = 0;
      const w = quizQuestionList[quizIndex];
      quizWordPos.textContent      = w.pos || 'N/A';
      quizWord.textContent         = w.word;
      quizPronunciation.textContent = w.pronunciation || '';
      hide(quizFeedback, quizNextBtn);
  
      quizOptions.innerHTML = '';
      generateQuizOptions(w).forEach((opt, idx) => {
        const btn = document.createElement('button');
        btn.className = 'quiz-option anim-up';
        btn.style.animationDelay = `${idx * 0.07}s`;
        btn.dataset.meaning = opt;
        btn.innerHTML = `
          <span class="quiz-option-letter">${String.fromCharCode(65 + idx)}</span>
          <span class="quiz-option-text">${opt}</span>
        `;
        btn.addEventListener('click', () => handleQuizAnswer(btn, opt, w.meaning));
        quizOptions.appendChild(btn);
      });
      quizProgressText.textContent = `${quizIndex + 1} / ${quizQuestionList.length}`;
      speak(w.word);
    }
  
    function handleQuizAnswer(selectedBtn, chosen, correct) {
      if (isAnswered) return;
      const allOpts = quizOptions.querySelectorAll('.quiz-option');
  
      if (chosen === correct) {
        isAnswered = true;
        quizScore += 10;
        scoreEl.textContent = quizScore;
        allOpts.forEach(o => {
          o.classList.add('disabled');
          if (o.dataset.meaning === correct) o.classList.add('correct');
        });
        feedbackText.textContent = 'Chính xác! 🎉';
        quizFeedback.classList.remove('incorrect');
        show(quizFeedback);
        hide(quizNextBtn);
        setTimeout(() => {
          quizIndex++;
          quizIndex < quizQuestionList.length ? loadQuizQuestion() : endQuiz();
        }, 1200);
      } else if (retryCount === 0) {
        retryCount++;
        selectedBtn.classList.add('incorrect');
        selectedBtn.style.pointerEvents = 'none';
        feedbackText.textContent = 'Sai rồi! Hãy thử lại lần nữa 💪';
        quizFeedback.classList.add('incorrect');
        show(quizFeedback);
      } else {
        isAnswered = true;
        allOpts.forEach(o => {
          o.classList.add('disabled');
          if (o.dataset.meaning === correct) o.classList.add('correct');
        });
        selectedBtn.classList.add('incorrect');
        feedbackText.textContent = `Đáp án đúng: ${correct}`;
        quizFeedback.classList.add('incorrect');
        show(quizFeedback);
        setTimeout(() => backToCategoryActions(), 1500);
      }
    }
  
    function endQuiz() {
      const quizCard     = quizContainer.querySelector('.quiz-card');
      const quizHeader   = quizContainer.querySelector('.quiz-header');
      const quizProgress = quizContainer.querySelector('.quiz-progress');
      hide(quizCard, quizHeader, quizProgress);
  
      const results = document.createElement('div');
      results.id = 'quiz-results-screen';
      results.innerHTML = `
        <div class="quiz-controls-top quiz-header">
          <div class="quiz-title-box">
            <span class="quiz-emoji">🏆</span>
            <h2>Kết quả</h2>
          </div>
        </div>
        <div class="quiz-card" style="margin-top:1rem">
          <div class="results-content">
            <i class="fa-solid fa-trophy results-trophy"></i>
            <h3 class="results-score">Điểm: ${quizScore}</h3>
            <p class="results-desc">Tuyệt vời! Bạn đã hoàn thành ${quizQuestionList.length} câu hỏi.</p>
            <div class="results-actions">
              <button class="btn btn-primary" id="restart-quiz">
                <i class="fa-solid fa-rotate-right"></i> Chơi lại
              </button>
              <button class="btn btn-secondary" id="back-to-category-quiz">
                <i class="fa-solid fa-arrow-left"></i> Chọn chế độ
              </button>
            </div>
          </div>
        </div>
      `;
      quizContainer.appendChild(results);
  
      document.getElementById('restart-quiz').addEventListener('click', () => {
        results.remove();
        show(quizCard, quizHeader, quizProgress);
        startQuiz();
      });
      document.getElementById('back-to-category-quiz').addEventListener('click', () => backToCategoryActions());
    }
  
    function backToCategoryActions() {
      hide(quizContainer, flashcardSection, controls);
      show(categoryActions, hubContainer);
      document.getElementById('quiz-results-screen')?.remove();
      setSelectionLayout(true);
    }
  
    backToHomeBtn?.addEventListener('click', () => { goBackHome(); });
    btnQuizBack?.addEventListener('click', () => { goBackToCategories(); });
    btnQuizSound?.addEventListener('click', e => {
      e.stopPropagation();
      speak(quizWord.textContent);
      btnQuizSound.style.transform = 'scale(.88)';
      setTimeout(() => btnQuizSound.style.transform = '', 160);
    });
  
    /* ─── Boot ─────────────────────────────────────────── */
    loadCategories();
  });