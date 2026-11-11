const QUESTIONS_PER_ROUND = 5;
const CHOICES = ["A", "B", "C", "D"];
const DIFFICULTIES = ["Easy", "Medium", "Hard"];
const POINTS_PER_ANSWER = 20;
const STREAK_BONUS = 5;
const MAX_ROUND_POINTS = QUESTIONS_PER_ROUND * POINTS_PER_ANSWER
  + (QUESTIONS_PER_ROUND - 1) * STREAK_BONUS;
const PERSONAL_BEST_KEY = "scienceShowdown.personalBest";

const elements = {
  loading: document.querySelector("#loading-state"),
  error: document.querySelector("#error-state"),
  poolCount: document.querySelector("#pool-count"),
  areaSelectionError: document.querySelector("#area-selection-error"),
  welcome: document.querySelector("#welcome-screen"),
  question: document.querySelector("#question-screen"),
  results: document.querySelector("#results-screen"),
  score: document.querySelector("#score-value"),
  bestScore: document.querySelector("#best-score"),
  roundCount: document.querySelector("#round-count"),
  streakStat: document.querySelector("#streak-stat"),
  streakCount: document.querySelector("#streak-count"),
  progressTrack: document.querySelector("#progress-track"),
  progress: document.querySelector("#progress-fill"),
  status: document.querySelector("#status-copy"),
  announcer: document.querySelector("#game-announcer"),
  questionNumber: document.querySelector("#question-number"),
  category: document.querySelector("#category-label"),
  difficultyLabel: document.querySelector("#difficulty-label"),
  questionText: document.querySelector("#question-text"),
  answers: document.querySelector("#answer-list"),
  feedbackRow: document.querySelector("#feedback-row"),
  feedbackCopy: document.querySelector(".feedback-copy"),
  feedbackTitle: document.querySelector("#feedback-title"),
  explanation: document.querySelector("#explanation-text"),
  next: document.querySelector("#next-button"),
  finalScore: document.querySelector("#final-score"),
  resultTitle: document.querySelector("#result-title"),
  resultCopy: document.querySelector("#result-copy"),
  resultSummary: document.querySelector("#result-summary"),
  missedReview: document.querySelector("#missed-review"),
  missedReviewList: document.querySelector("#missed-review-list"),
};

let questions = [];
let roundQuestions = [];
let questionIndex = 0;
let correctAnswers = 0;
let scorePoints = 0;
let currentStreak = 0;
let personalBest = 0;
let personalBestAvailable = true;
let locked = false;
let answerResults = [];

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    if (quoted) {
      if (character === '"' && text[index + 1] === '"') {
        field += '"';
        index += 1;
      } else if (character === '"') {
        quoted = false;
      } else {
        field += character;
      }
    } else if (character === '"') {
      quoted = true;
    } else if (character === ",") {
      row.push(field);
      field = "";
    } else if (character === "\n") {
      row.push(field.replace(/\r$/, ""));
      if (row.some((value) => value.trim())) rows.push(row);
      row = [];
      field = "";
    } else {
      field += character;
    }
  }

  if (field || row.length) {
    row.push(field.replace(/\r$/, ""));
    if (row.some((value) => value.trim())) rows.push(row);
  }
  if (quoted) throw new Error("The question file contains an unfinished quoted field.");

  const [headers, ...records] = rows;
  if (!headers) throw new Error("The question file is empty.");
  return records.map((values) => Object.fromEntries(
    headers.map((header, index) => [header.trim(), (values[index] || "").trim()]),
  ));
}

function shuffle(items) {
  const shuffled = [...items];
  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1));
    [shuffled[index], shuffled[swapIndex]] = [shuffled[swapIndex], shuffled[index]];
  }
  return shuffled;
}

function showScreen(screen) {
  [elements.welcome, elements.question, elements.results].forEach((item) => {
    item.hidden = item !== screen;
  });
}

function announce(message) {
  elements.announcer.textContent = message;
}

function updateScoreboard() {
  const answeredQuestions = Math.min(
    questionIndex + (locked ? 1 : 0),
    QUESTIONS_PER_ROUND,
  );
  elements.score.textContent = String(scorePoints).padStart(2, "0");
  elements.roundCount.textContent = `${String(answeredQuestions).padStart(2, "0")} / ${String(QUESTIONS_PER_ROUND).padStart(2, "0")}`;
  elements.progress.style.width = `${(answeredQuestions / QUESTIONS_PER_ROUND) * 100}%`;
  elements.progressTrack.setAttribute("aria-valuenow", String(answeredQuestions));
  elements.progressTrack.setAttribute(
    "aria-valuetext",
    `${answeredQuestions} of ${QUESTIONS_PER_ROUND} questions answered`,
  );
  elements.streakStat.hidden = currentStreak === 0;
  elements.streakCount.textContent = `${currentStreak}×`;
}

function getSelectedAreas() {
  return new Set(
    [...document.querySelectorAll('input[name="science-area"]:checked')]
      .map((input) => input.value),
  );
}

function getSelectedDifficulty() {
  const selectedDifficulty = document.querySelector('input[name="difficulty"]:checked');
  if (!selectedDifficulty) throw new Error("Choose a difficulty before starting a round.");
  return selectedDifficulty.value;
}

function getEligibleQuestions(selectedAreas = getSelectedAreas()) {
  return questions.filter((question) => (
    selectedAreas.has(question.category)
    && question.difficulty === getSelectedDifficulty()
  ));
}

function updateQuestionPoolCount() {
  elements.poolCount.textContent = `${getEligibleQuestions().length} ${getSelectedDifficulty().toUpperCase()} QUESTIONS AVAILABLE`;
}

function updatePersonalBestDisplay() {
  elements.bestScore.textContent = personalBestAvailable ? `${personalBest} PTS` : "N/A";
}

function loadPersonalBest() {
  try {
    const savedScore = window.localStorage.getItem(PERSONAL_BEST_KEY);
    if (savedScore !== null) {
      const parsedScore = Number(savedScore);
      if (!Number.isInteger(parsedScore) || parsedScore < 0 || parsedScore > MAX_ROUND_POINTS) {
        throw new Error("Saved personal best is not a valid score.");
      }
      personalBest = parsedScore;
    }
  } catch (error) {
    personalBestAvailable = false;
    console.error("Could not load the personal best from local storage.", error);
  }
  updatePersonalBestDisplay();
}

function savePersonalBestIfBeaten() {
  if (!personalBestAvailable || scorePoints <= personalBest) return false;
  try {
    window.localStorage.setItem(PERSONAL_BEST_KEY, String(scorePoints));
    personalBest = scorePoints;
    updatePersonalBestDisplay();
    return true;
  } catch (error) {
    personalBestAvailable = false;
    updatePersonalBestDisplay();
    console.error("Could not save the personal best to local storage.", error);
    return false;
  }
}

function selectBalancedQuestions(selectedAreas, difficulty) {
  const categories = [...selectedAreas]
    .map((category) => ({
      category,
      questions: shuffle(questions.filter((question) => (
        question.category === category && question.difficulty === difficulty
      ))),
      selected: 0,
    }))
    .filter((group) => group.questions.length > 0);
  const selectedQuestions = [];

  while (selectedQuestions.length < QUESTIONS_PER_ROUND) {
    const available = categories.filter((group) => group.questions.length > 0);
    const fewestSelected = Math.min(...available.map((group) => group.selected));
    const candidates = available.filter((group) => group.selected === fewestSelected);
    const group = candidates[Math.floor(Math.random() * candidates.length)];
    selectedQuestions.push(group.questions.pop());
    group.selected += 1;
  }

  return shuffle(selectedQuestions);
}

function startGame() {
  const selectedAreas = getSelectedAreas();
  if (selectedAreas.size === 0) {
    elements.areaSelectionError.hidden = false;
    elements.areaSelectionError.focus();
    return;
  }

  const selectedDifficulty = getSelectedDifficulty();
  const eligibleQuestions = getEligibleQuestions(selectedAreas);
  if (eligibleQuestions.length < QUESTIONS_PER_ROUND) {
    elements.areaSelectionError.textContent = `There aren't enough ${selectedDifficulty.toLowerCase()} questions in those areas for a round.`;
    elements.areaSelectionError.hidden = false;
    elements.areaSelectionError.focus();
    return;
  }

  elements.areaSelectionError.hidden = true;
  roundQuestions = selectBalancedQuestions(selectedAreas, selectedDifficulty);
  questionIndex = 0;
  correctAnswers = 0;
  scorePoints = 0;
  currentStreak = 0;
  locked = false;
  answerResults = [];
  elements.status.textContent = "ROUND IN PROGRESS";
  updateScoreboard();
  showScreen(elements.question);
  renderQuestion();
  elements.questionText.focus();
}

function renderQuestion() {
  const question = roundQuestions[questionIndex];
  locked = false;
  elements.questionNumber.textContent = `QUESTION ${String(questionIndex + 1).padStart(2, "0")} / ${String(QUESTIONS_PER_ROUND).padStart(2, "0")}`;
  elements.category.textContent = question.category.toUpperCase();
  elements.category.dataset.category = question.category.toLowerCase().replace(/\s+/g, "-");
  elements.difficultyLabel.textContent = question.difficulty.toUpperCase();
  elements.questionText.textContent = question.question;
  elements.questionText.setAttribute(
    "aria-label",
    `${question.category}, ${question.difficulty}. ${question.question}`,
  );
  elements.feedbackRow.hidden = true;
  elements.feedbackCopy.className = "feedback-copy";
  elements.answers.replaceChildren();

  CHOICES.forEach((choice) => {
    const button = document.createElement("button");
    button.className = "answer-option";
    button.type = "button";
    button.dataset.choice = choice;
    button.innerHTML = `<span class="answer-key">${choice}</span><span></span>`;
    button.lastElementChild.textContent = question[choice];
    button.addEventListener("click", () => submitAnswer(choice));
    elements.answers.append(button);
  });
}

function submitAnswer(choice) {
  if (locked) return;
  locked = true;
  const question = roundQuestions[questionIndex];
  const isCorrect = choice === question.answer.trim().toUpperCase();
  let pointsAwarded = 0;
  if (isCorrect) {
    correctAnswers += 1;
    currentStreak += 1;
    pointsAwarded = POINTS_PER_ANSWER + (currentStreak > 1 ? STREAK_BONUS : 0);
    scorePoints += pointsAwarded;
  } else {
    currentStreak = 0;
  }
  answerResults.push({ question, choice, isCorrect });
  updateScoreboard();

  elements.answers.querySelectorAll(".answer-option").forEach((button) => {
    button.disabled = true;
    if (button.dataset.choice === question.answer.trim().toUpperCase()) {
      button.classList.add("correct");
    } else if (button.dataset.choice === choice) {
      button.classList.add("incorrect");
    } else {
      button.classList.add("muted");
    }
  });

  elements.feedbackCopy.classList.add(isCorrect ? "is-correct" : "is-wrong");
  elements.feedbackTitle.textContent = isCorrect
    ? `Correct: ${question[question.answer.trim().toUpperCase()]}. +${pointsAwarded} points${currentStreak > 1 ? `, including a +${STREAK_BONUS} streak bonus` : ""}.`
    : `Not quite. The correct answer is ${question[question.answer.trim().toUpperCase()]}.`;
  elements.explanation.textContent = question.explanation;
  announce(`${isCorrect ? "Correct." : "Not quite."} Score: ${scorePoints} points. ${answeredQuestionCount()} of ${QUESTIONS_PER_ROUND} questions answered.${currentStreak > 0 ? ` Current streak: ${currentStreak}.` : ""}`);
  elements.next.innerHTML = questionIndex === QUESTIONS_PER_ROUND - 1
    ? 'SEE RESULTS <span aria-hidden="true">→</span>'
    : 'NEXT <span aria-hidden="true">→</span>';
  elements.feedbackRow.hidden = false;
  elements.next.focus();
}

function showResults() {
  questionIndex = QUESTIONS_PER_ROUND;
  updateScoreboard();
  const percentage = Math.round((correctAnswers / QUESTIONS_PER_ROUND) * 100);
  elements.finalScore.textContent = String(percentage).padStart(2, "0");
  elements.resultTitle.textContent = percentage === 100
    ? "Perfect score."
    : percentage >= 60 ? "Nice work." : "Keep exploring.";
  const newPersonalBest = savePersonalBestIfBeaten();
  const bestCopy = personalBestAvailable ? ` Personal best: ${personalBest} points.` : " Personal best storage is unavailable.";
  elements.resultCopy.textContent = `You got ${correctAnswers} out of ${QUESTIONS_PER_ROUND} questions right and scored ${scorePoints} points.${newPersonalBest ? " New personal best!" : bestCopy}`;
  elements.resultSummary.replaceChildren(...answerResults.map(({ isCorrect }) => {
    const mark = document.createElement("span");
    mark.className = `result-mark ${isCorrect ? "correct" : "incorrect"}`;
    mark.setAttribute("aria-label", isCorrect ? "Correct" : "Incorrect");
    return mark;
  }));
  const missedAnswers = answerResults.filter(({ isCorrect }) => !isCorrect);
  elements.missedReview.hidden = missedAnswers.length === 0;
  elements.missedReviewList.replaceChildren(...missedAnswers.map(({ question, choice }) => {
    const item = document.createElement("article");
    item.className = "missed-review-item";

    const category = document.createElement("span");
    category.className = "missed-review-category";
    category.textContent = question.category;

    const prompt = document.createElement("h3");
    prompt.textContent = question.question;

    const yourAnswer = document.createElement("p");
    yourAnswer.className = "missed-review-answer";
    yourAnswer.textContent = `Your answer: ${question[choice]}`;

    const correctAnswer = document.createElement("p");
    correctAnswer.className = "missed-review-correct";
    correctAnswer.textContent = `Correct answer: ${question[question.answer.trim().toUpperCase()]}`;

    const explanation = document.createElement("p");
    explanation.className = "missed-review-explanation";
    explanation.textContent = question.explanation;

    item.append(category, prompt, yourAnswer, correctAnswer, explanation);
    return item;
  }));
  elements.status.textContent = "ROUND COMPLETE";
  showScreen(elements.results);
  elements.resultTitle.focus();
}

function answeredQuestionCount() {
  return Math.min(questionIndex + (locked ? 1 : 0), QUESTIONS_PER_ROUND);
}

elements.next.addEventListener("click", () => {
  if (questionIndex === QUESTIONS_PER_ROUND - 1) {
    showResults();
    return;
  }
  questionIndex += 1;
  locked = false;
  updateScoreboard();
  renderQuestion();
  elements.questionText.focus();
});

document.querySelector("#start-button").addEventListener("click", startGame);
document.querySelector("#play-again-button").addEventListener("click", startGame);
document.querySelectorAll('input[name="science-area"]').forEach((input) => {
  input.addEventListener("change", () => {
    elements.areaSelectionError.hidden = true;
    updateQuestionPoolCount();
  });
});
document.querySelectorAll('input[name="difficulty"]').forEach((input) => {
  input.addEventListener("change", () => {
    elements.areaSelectionError.hidden = true;
    updateQuestionPoolCount();
  });
});
document.querySelector("#reset-button").addEventListener("click", () => {
  correctAnswers = 0;
  scorePoints = 0;
  currentStreak = 0;
  questionIndex = 0;
  locked = false;
  elements.status.textContent = "READY WHEN YOU ARE";
  updateScoreboard();
  showScreen(elements.welcome);
  document.querySelector("#start-button").focus();
});

loadPersonalBest();

document.addEventListener("keydown", (event) => {
  if (elements.question.hidden) return;
  const target = event.target;
  if (
    event.altKey || event.ctrlKey || event.metaKey || event.isComposing
    || target instanceof HTMLElement
      && (target.isContentEditable || target.matches("button, input, select, textarea, a"))
  ) return;
  if (!locked && /^[a-d]$/i.test(event.key)) {
    submitAnswer(event.key.toUpperCase());
  }
});

fetch("questions.csv")
  .then((response) => {
    if (!response.ok) throw new Error(`Could not load questions.csv (${response.status}).`);
    return response.text();
  })
  .then((csv) => {
    questions = parseCsv(csv);
    const invalidDifficulty = questions.some((question) => !DIFFICULTIES.includes(question.difficulty));
    if (invalidDifficulty) {
      throw new Error("Every question must have an Easy, Medium, or Hard difficulty in questions.csv.");
    }
    if (questions.length < QUESTIONS_PER_ROUND) {
      throw new Error(`Add at least ${QUESTIONS_PER_ROUND} questions to questions.csv.`);
    }
    updateQuestionPoolCount();
    elements.loading.hidden = true;
    showScreen(elements.welcome);
  })
  .catch((error) => {
    elements.loading.hidden = true;
    elements.error.textContent = `${error.message} Start a local server from the day03 folder to play.`;
    elements.error.hidden = false;
  });