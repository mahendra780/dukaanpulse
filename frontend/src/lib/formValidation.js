

const PLACEHOLDER_NAMES = {
  Qty: "quantity",
  Price: "price",
  "Unit price": "unit price",
  Discount: "discount",
  Tax: "tax",
  Received: "received quantity",
  "Conv. to base": "conversion to base",
  "Unit name (e.g. CARTON)": "unit name",
};


function lowerFirstWord(text) {
  const firstWord = text.split(/\s+/)[0];
  const isAcronym = firstWord.length > 1 && firstWord === firstWord.toUpperCase();
  return isAcronym ? text : text.charAt(0).toLowerCase() + text.slice(1);
}

function cleanLabel(text) {
  return lowerFirstWord(
    text
      .replace(/\s*\(.*?\)/g, "")
      .replace(/[.:*]+\s*$/, "")
      .trim()
  );
}

function capitalize(text) {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function friendlyName(el) {
  const label = el.closest?.(".field")?.querySelector("label")?.textContent;
  if (label && label.trim()) return cleanLabel(label);

  const placeholder = el.getAttribute?.("placeholder");
  if (placeholder) return PLACEHOLDER_NAMES[placeholder] || cleanLabel(placeholder);

  return null;
}

function nounFromFirstOption(el) {
  const text = el.options?.[0]?.text || "";
  const noun = text.replace(/^select\s+/i, "").replace(/(…|\.\.\.)\s*$/, "").trim().toLowerCase();
  return noun || null;
}

export function messageFor(el) {
  const v = el.validity;
  if (!v || v.valid) return null;

  const name = friendlyName(el);
  const isSelect = el.tagName === "SELECT";
  const isDate = el.type === "date";
  const subject = name ? `the ${name}` : "this value";
  const Subject = name ? capitalize(name) : "This value";

  if (v.valueMissing) {
    if (isSelect) {
      const noun = name || nounFromFirstOption(el);
      return noun ? `Please select ${name ? "the" : "a"} ${noun}.` : "Please select an option.";
    }
    return isDate ? `Please select ${subject}.` : `Please enter ${subject}.`;
  }

  if (v.badInput) return `Please enter a valid ${name || "number"}.`;

  if (v.rangeUnderflow) {
    const min = Number(el.min);
    if (min === 0) return `${Subject} can't be negative.`;
    if (min > 0 && min < 1) return `${Subject} must be greater than 0.`;
    return `${Subject} must be at least ${el.min}.`;
  }

  if (v.rangeOverflow) return `${Subject} can't be more than ${el.max}.`;

  if (v.tooShort) return `${Subject} must be at least ${el.minLength} characters.`;
  if (v.tooLong) return `${Subject} can't be longer than ${el.maxLength} characters.`;

  if (v.stepMismatch) return `${Subject} must be a whole number.`;
  if (v.typeMismatch) return `Please enter a valid ${name || "value"}.`;
  if (v.patternMismatch) return `Please enter ${subject} in the correct format.`;

  return null;
}

export function installFriendlyValidation() {
  const onInvalid = (e) => {
    const message = messageFor(e.target);
    if (message) e.target.setCustomValidity(message);
  };
  const clear = (e) => {
    if (typeof e.target?.setCustomValidity === "function") e.target.setCustomValidity("");
  };

  document.addEventListener("invalid", onInvalid, true);
  document.addEventListener("input", clear, true);
  document.addEventListener("change", clear, true);

  return () => {
    document.removeEventListener("invalid", onInvalid, true);
    document.removeEventListener("input", clear, true);
    document.removeEventListener("change", clear, true);
  };
}