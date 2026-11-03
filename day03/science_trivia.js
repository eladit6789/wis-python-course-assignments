const QUESTIONS_PER_ROUND = 5;
const CHOICES = ["A", "B", "C", "D"];

const elements = {
  loading: document.querySelector("#loading-state"),
  error: document.querySelector("#error-state"),
  poolCount: document.querySelector("#pool-count"),
  areaSelectionError: document.querySelector("#area-selection-error"),
  welcome: document.querySelector("#welcome-screen"),
  question: document.querySelector("#question-screen"),
  results: document.querySelector("#results-screen"),
  score: document.querySelector("#score-value"),
  roundCount: document.querySelector("#round-count"),
  progress: document.querySelector("#progress-fill"),
  status: document.querySelector("#status-copy"),
  questionNumber: document.querySelector("#question-number"),
  category: document.querySelector("#category-label"),
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
};

let questions = [];
let roundQuestions = [];
let questionIndex = 0;
let correctAnswers = 0;
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

function updateScoreboard() {
  elements.score.textContent = String(correctAnswers * 20).padStart(2, "0");
  elements.roundCount.textContent = `${String(questionIndex).padStart(2, "0")} / ${String(QUESTIONS_PER_ROUND).padStart(2, "0")}`;
  elements.progress.style.width = `${(questionIndex / QUESTIONS_PER_ROUND) * 100}%`;
}

function startGame() {
  const selectedAreas = new Set(
    [...document.querySelectorAll('input[name="science-area"]:checked')]
      .map((input) => input.value),
  );
  if (selectedAreas.size === 0) {
    elements.areaSelectionError.hidden = false;
    return;
  }

  const eligibleQuestions = questions.filter((question) => selectedAreas.has(question.category));
  if (eligibleQuestions.length < QUESTIONS_PER_ROUND) {
    elements.areaSelectionError.textContent = "There aren't enough questions in those areas for a round.";
    elements.areaSelectionError.hidden = false;
    return;
  }

  elements.areaSelectionError.hidden = true;
  roundQuestions = shuffle(eligibleQuestions).slice(0, QUESTIONS_PER_ROUND);
  questionIndex = 0;
  correctAnswers = 0;
  answerResults = [];
  elements.status.textContent = "ROUND IN PROGRESS";
  updateScoreboard();
  showScreen(elements.question);
  renderQuestion();
}

function renderQuestion() {
  const question = roundQuestions[questionIndex];
  locked = false;
  elements.questionNumber.textContent = `QUESTION ${String(questionIndex + 1).padStart(2, "0")} / ${String(QUESTIONS_PER_ROUND).padStart(2, "0")}`;
  elements.category.textContent = question.category.toUpperCase();
  elements.questionText.textContent = question.question;
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
  if (isCorrect) correctAnswers += 1;
  answerResults.push(isCorrect);
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
  elements.feedbackTitle.textContent = isCorrect ? "That's right." : `The answer was ${question.answer.trim().toUpperCase()}.`;
  elements.explanation.textContent = question.explanation;
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
  elements.resultCopy.textContent = `You got ${correctAnswers} out of ${QUESTIONS_PER_ROUND} questions right. There is always more to discover.`;
  elements.resultSummary.replaceChildren(...answerResults.map((isCorrect) => {
    const mark = document.createElement("span");
    mark.className = `result-mark ${isCorrect ? "correct" : "incorrect"}`;
    mark.setAttribute("aria-label", isCorrect ? "Correct" : "Incorrect");
    return mark;
  }));
  elements.status.textContent = "ROUND COMPLETE";
  showScreen(elements.results);
}

elements.next.addEventListener("click", () => {
  if (questionIndex === QUESTIONS_PER_ROUND - 1) {
    showResults();
    return;
  }
  questionIndex += 1;
  updateScoreboard();
  renderQuestion();
});

document.querySelector("#start-button").addEventListener("click", startGame);
document.querySelector("#play-again-button").addEventListener("click", startGame);
document.querySelectorAll('input[name="science-area"]').forEach((input) => {
  input.addEventListener("change", () => {
    elements.areaSelectionError.hidden = true;
  });
});
document.querySelector("#reset-button").addEventListener("click", () => {
  correctAnswers = 0;
  questionIndex = 0;
  elements.status.textContent = "READY WHEN YOU ARE";
  updateScoreboard();
  showScreen(elements.welcome);
});

document.addEventListener("keydown", (event) => {
  if (elements.question.hidden) return;
  if (!locked && /^[a-d]$/i.test(event.key)) {
    submitAnswer(event.key.toUpperCase());
  } else if (locked && event.key === "Enter") {
    elements.next.click();
  }
});

fetch("questions.csv")
  .then((response) => {
    if (!response.ok) throw new Error(`Could not load questions.csv (${response.status}).`);
    return response.text();
  })
  .then((csv) => {
    questions = parseCsv(csv);
    elements.poolCount.textContent = `${questions.length} QUESTIONS IN POOL`;
    if (questions.length < QUESTIONS_PER_ROUND) {
      throw new Error(`Add at least ${QUESTIONS_PER_ROUND} questions to questions.csv.`);
    }
    elements.loading.hidden = true;
    showScreen(elements.welcome);
  })
  .catch((error) => {
    elements.loading.hidden = true;
    elements.error.textContent = `${error.message} Start a local server from the day03 folder to play.`;
    elements.error.hidden = false;
  });