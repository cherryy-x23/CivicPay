import API_BASE_URL from "../config.js";
import { useEffect, useState } from "react";
import "./Home.css";
import {
  getAccessToken,
  getCurrentUser,
  logout,
} from "../auth.js";

function decodeJwtPayload(token) {
  if (!token || typeof token !== "string") return null;

  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;

    const normalized = parts[1]
      .replace(/-/g, "+")
      .replace(/_/g, "/");

    const padded = normalized.padEnd(
      normalized.length + ((4 - (normalized.length % 4)) % 4),
      "="
    );

    return JSON.parse(window.atob(padded));
  } catch {
    return null;
  }
}

function isTokenExpired(token) {
  const payload = decodeJwtPayload(token);

  if (!payload?.exp) return false;

  return Number(payload.exp) * 1000 <= Date.now();
}

function Home() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [checkedSteps, setCheckedSteps] = useState([]);
  const [copiedField, setCopiedField] = useState("");
  const [sessionMessage, setSessionMessage] = useState("");
  const [analysisHistory, setAnalysisHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState("");
  const [sessionRemainingSeconds, setSessionRemainingSeconds] = useState(null);

  // =====================================================
  // PHASE 6.3.5 — FRONTEND SESSION PROTECTION
  // =====================================================

  useEffect(() => {
    const checkSession = () => {
      const token = getAccessToken();

      if (!token || isTokenExpired(token)) {
        logout();
        window.location.href = "/login";
      }
    };

    checkSession();

    const sessionTimer = window.setInterval(checkSession, 30000);

    return () => {
      window.clearInterval(sessionTimer);
    };
  }, []);

  // =====================================================
  // PHASE 6.5.2 — SESSION SECURITY PANEL
  // =====================================================

  useEffect(() => {
    const updateSessionRemaining = () => {
      const token = getAccessToken();
      const payload = decodeJwtPayload(token);

      if (!token || !payload?.exp) {
        setSessionRemainingSeconds(null);
        return;
      }

      const remaining = Math.max(
        0,
        Math.floor(
          (Number(payload.exp) * 1000 - Date.now()) / 1000
        )
      );

      setSessionRemainingSeconds(remaining);

      if (remaining <= 0) {
        logout();
        window.location.href = "/login";
      }
    };

    updateSessionRemaining();

    const sessionCountdownTimer = window.setInterval(
      updateSessionRemaining,
      1000
    );

    return () => {
      window.clearInterval(sessionCountdownTimer);
    };
  }, []);

  // =====================================================
  // PHASE 6.4.3 — SECURE ANALYSIS HISTORY
  // =====================================================

  const fetchAnalysisHistory = async () => {
    const token = getAccessToken();

    if (!token || isTokenExpired(token)) {
      logout();
      window.location.href = "/login";
      return;
    }

    setHistoryLoading(true);
    setHistoryError("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/analysis-history`,
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      const responseText = await response.text();
      let data = null;

      try {
        data = responseText ? JSON.parse(responseText) : null;
      } catch {
        throw new Error(
          "CivicPay returned an invalid history response."
        );
      }

      if (response.status === 401) {
        logout();
        window.location.href = "/login";
        return;
      }

      if (!response.ok) {
        throw new Error(
          data?.detail ||
            "Unable to retrieve your analysis history."
        );
      }

      const safeHistory = Array.isArray(data?.history)
        ? data.history.map((item) => ({
            analysis_id: item?.analysis_id || "Unavailable",
            risk_level: item?.risk_level || "UNKNOWN",
            risk_score: Number(item?.risk_score ?? 0),
            verification_status:
              item?.verification_status || "incomplete",
            verification_confidence:
              Number(item?.verification_confidence ?? 0),
            ai_decision:
              item?.ai_decision || "REVIEW_REQUIRED",
            created_at: item?.created_at || "Unavailable",
          }))
        : [];

      setAnalysisHistory(safeHistory);
    } catch (err) {
      setHistoryError(
        err?.message ||
          "Unable to load your analysis history."
      );
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalysisHistory();
  }, []);

  const getHistoryRiskClass = (riskLevel) => {
    const level = String(riskLevel || "unknown").toLowerCase();
    return `history-risk-${level}`;
  };

  const getHistoryRiskIcon = (riskLevel) => {
    const level = String(riskLevel || "").toLowerCase();

    if (level === "low") return "🛡️";
    if (level === "medium") return "⚠️";
    if (level === "high") return "🚨";
    return "🔎";
  };

  const formatHistoryDate = (value) => {
    if (!value || value === "Unavailable") {
      return "Time unavailable";
    }

    const parsed = new Date(
      String(value).replace(" ", "T")
    );

    if (Number.isNaN(parsed.getTime())) {
      return String(value);
    }

    return parsed.toLocaleString();
  };

  // =====================================================
  // PHASE 3.3 — ANALYSIS ANIMATION
  // =====================================================

  const [analysisStep, setAnalysisStep] = useState(0);
  const [displayedRiskScore, setDisplayedRiskScore] = useState(0);

  const analysisStages = [
    {
      number: "01",
      title: "DETECT",
      description: "Payment signals identified",
      icon: "🔍",
    },
    {
      number: "02",
      title: "INVESTIGATE",
      description: "Evidence examined",
      icon: "🧠",
    },
    {
      number: "03",
      title: "EXPLAIN",
      description: "Risk reasoning generated",
      icon: "✦",
    },
    {
      number: "04",
      title: "VERIFY",
      description: "Security checks performed",
      icon: "✓",
    },
    {
      number: "05",
      title: "RECOMMEND",
      description: "Final action determined",
      icon: "🛡️",
    },
  ];

  // =====================================================
  // PHASE 3.3 — ANIMATED RISK SCORE
  // =====================================================

  useEffect(() => {
    const target = Number(
      result?.risk_analysis?.risk_score ?? 0
    );

    if (!result) {
      setDisplayedRiskScore(0);
      return;
    }

    setDisplayedRiskScore(0);

    const duration = 900;
    const startTime = performance.now();

    const animate = (currentTime) => {
      const elapsed = currentTime - startTime;

      const progress = Math.min(
        elapsed / duration,
        1
      );

      const eased =
        1 - Math.pow(1 - progress, 3);

      setDisplayedRiskScore(
        Math.round(target * eased)
      );

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };

    requestAnimationFrame(animate);
  }, [result]);

  // =====================================================
  // CLEAN UP PREVIEW URL
  // =====================================================

  useEffect(() => {
    return () => {
      if (preview) {
        URL.revokeObjectURL(preview);
      }
    };
  }, [preview]);

  // =====================================================
  // RESET VERIFICATION STATE
  // =====================================================

  useEffect(() => {
    setCheckedSteps([]);
    setCopiedField("");
  }, [result]);

  // =====================================================
  // FILE SELECTION
  // =====================================================

  const handleFileChange = (event) => {
    const file = event.target.files[0];

    if (!file) return;

    const allowedTypes = [
      "image/png",
      "image/jpeg",
      "image/jpg",
    ];

    if (!allowedTypes.includes(file.type)) {
      setError("Unsupported file type. Please upload a PNG, JPG or JPEG image.");
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setError("This image is larger than 10 MB. Please choose a smaller screenshot.");
      return;
    }

    if (preview) {
      URL.revokeObjectURL(preview);
    }

    setSelectedFile(file);

    const imageURL = URL.createObjectURL(file);

    setPreview(imageURL);

    setResult(null);
    setError("");
    setSessionMessage("");

    setAnalysisStep(0);
    setDisplayedRiskScore(0);
  };

  // =====================================================
  // REMOVE FILE
  // =====================================================

  const removeFile = () => {
    if (preview) {
      URL.revokeObjectURL(preview);
    }

    setSelectedFile(null);
    setPreview(null);
    setResult(null);
    setError("");
    setSessionMessage("");

    setAnalysisStep(0);
    setDisplayedRiskScore(0);
  };

  // =====================================================
  // ANALYZE PAYMENT
  // =====================================================

  const analyzePayment = async () => {
  if (!selectedFile || loading) return;

  setLoading(true);
  setError("");
  setResult(null);
  setCheckedSteps([]);
  setCopiedField("");
  setAnalysisStep(0);
  setDisplayedRiskScore(0);

  const stepTimer = setInterval(() => {
    setAnalysisStep((current) => {
      if (current >= analysisStages.length - 1) {
        return current;
      }
      return current + 1;
    });
  }, 850);

  const controller = new AbortController();

  const timeoutId = setTimeout(
    () => controller.abort(),
    120000
  );

  try {
    const token = getAccessToken();

    if (!token || isTokenExpired(token)) {
      logout();
      window.location.href = "/login";
      return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile);

    const response = await fetch(
      `${API_BASE_URL}/analyze`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
        signal: controller.signal,
      }
    );

    const responseText = await response.text();

    let data;

    try {
      data = responseText
        ? JSON.parse(responseText)
        : null;
    } catch {
      throw new Error(
        "The CivicPay backend returned an invalid response."
      );
    }

    if (response.status === 401) {
      logout();

      setSessionMessage(
        "Your CivicPay session has expired. Please sign in again."
      );

      window.location.href = "/login";
      return;
    }

    if (!response.ok) {
      const detail =
        data?.detail ||
        data?.message ||
        `Server returned error ${response.status}.`;

      throw new Error(detail);
    }

    if (!data || typeof data !== "object") {
      throw new Error(
        "CivicPay received an empty analysis result."
      );
    }

    if (
      !data.risk_analysis ||
      typeof data.risk_analysis !== "object"
    ) {
      throw new Error(
        "The analysis completed, but no risk assessment was returned."
      );
    }

    // Do not log analysis results in the browser console.
    // Payment details, OCR content and QR data are sensitive.

    setResult(data);
    setAnalysisStep(4);

    fetchAnalysisHistory();

    setTimeout(() => {
      document
        .getElementById("investigation-result")
        ?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
    }, 150);

  } catch (err) {
    // Do not expose payment evidence or backend details
    // through browser developer-console logs.

    if (err?.name === "AbortError") {
      setError(
        "The analysis took too long. Please check that the CivicPay backend and AI service are running, then try again."
      );
    } else if (err instanceof TypeError) {
      setError(
        "CivicPay could not reach the backend. Start the FastAPI server and try again."
      );
    } else {
      setError(
        err?.message ||
        "Unable to analyze the payment. Please try again."
      );
    }

  } finally {
    clearInterval(stepTimer);
    clearTimeout(timeoutId);
    setLoading(false);
  }
};
// =====================================================
// ANALYZE ANOTHER PAYMENT
// =====================================================

const analyzeAnother = () => {
  if (preview) {
    URL.revokeObjectURL(preview);
  }

  setSelectedFile(null);
  setPreview(null);
  setResult(null);
  setError("");
  setSessionMessage("");

  setAnalysisStep(0);
  setDisplayedRiskScore(0);
  setCheckedSteps([]);
  setCopiedField("");

  window.scrollTo({
    top: 0,
    behavior: "smooth",
  });
};
  // =====================================================
  // RISK CLASS
  // =====================================================

  const getRiskClass = (riskLevel) => {
    if (!riskLevel) {
      return "unknown";
    }

    return riskLevel.toLowerCase();
  };

  // =====================================================
  // RISK ICON
  // =====================================================

  const getRiskIcon = (riskLevel) => {
    const level =
      riskLevel?.toLowerCase();

    if (level === "low") {
      return "🛡️";
    }

    if (level === "medium") {
      return "⚠️";
    }

    if (level === "high") {
      return "🚨";
    }

    return "🔎";
  };

  // =====================================================
  // RISK MESSAGE
  // =====================================================

  const getRiskMessage = (riskLevel) => {
    const level =
      riskLevel?.toLowerCase();

    if (level === "low") {
      return "No major risk signals were detected.";
    }

    if (level === "medium") {
      return "Some warning signals require your attention.";
    }

    if (level === "high") {
      return "Strong warning signals were detected. Be careful before paying.";
    }

    return "CivicPay could not confidently determine the payment risk.";
  };

  // =====================================================
  // INVESTIGATION STATUS
  // =====================================================

  const getInvestigationStatus = (type) => {
    const payment = result?.payment;
    const qr = result?.qr_analysis;
    const qrDetails =
      result?.risk_analysis?.qr_details;

    switch (type) {
      // ---------------------------------------------------
      // AMOUNT
      // ---------------------------------------------------

      case "amount":
        if (
          payment?.amount !== null &&
          payment?.amount !== undefined
        ) {
          return {
            status: "available",
            icon: "✓",
            label: "Available",
            description:
              "Payment amount was detected.",
          };
        }

        return {
          status: "warning",
          icon: "!",
          label: "Needs Review",
          description:
            "Payment amount could not be verified.",
        };

      // ---------------------------------------------------
      // RECIPIENT
      // ---------------------------------------------------

      case "recipient":
        if (payment?.merchant) {
          return {
            status: "available",
            icon: "✓",
            label: "Available",
            description:
              "Recipient information was detected.",
          };
        }

        if (qrDetails?.payee_name) {
          return {
            status: "available",
            icon: "✓",
            label: "QR Verified",
            description:
              "Recipient was found from the QR code.",
          };
        }

        return {
          status: "warning",
          icon: "!",
          label: "Needs Review",
          description:
            "Recipient could not be confidently identified.",
        };

      // ---------------------------------------------------
      // QR
      // ---------------------------------------------------

      case "qr":
        if (qr?.detected) {
          return {
            status: "available",
            icon: "✓",
            label: "Detected",
            description:
              "QR code was successfully decoded.",
          };
        }

        return {
          status: "warning",
          icon: "!",
          label: "Not Detected",
          description:
            "No readable QR code was found.",
        };

      // ---------------------------------------------------
      // TRANSACTION ID
      // ---------------------------------------------------

      case "transaction":
        if (payment?.transaction_id) {
          return {
            status: "available",
            icon: "✓",
            label: "Available",
            description:
              "Transaction ID was detected.",
          };
        }

        return {
          status: "warning",
          icon: "!",
          label: "Missing",
          description:
            "Transaction ID was not found.",
        };

      // ---------------------------------------------------
      // UTR
      // ---------------------------------------------------

      case "utr":
        if (payment?.utr) {
          return {
            status: "available",
            icon: "✓",
            label: "Available",
            description:
              "UTR number was detected.",
          };
        }

        return {
          status: "warning",
          icon: "!",
          label: "Missing",
          description:
            "UTR number was not found.",
        };

      // ---------------------------------------------------
      // PAYMENT STATUS
      // ---------------------------------------------------

      case "status":
        if (
          payment?.payment_status &&
          payment.payment_status.toLowerCase() !==
            "unknown"
        ) {
          return {
            status: "available",
            icon: "✓",
            label: "Verified",
            description:
              "Payment status was identified.",
          };
        }

        return {
          status: "warning",
          icon: "!",
          label: "Unknown",
          description:
            "Payment status could not be confidently verified.",
        };

      default:
        return {
          status: "warning",
          icon: "!",
          label: "Unknown",
          description:
            "Information could not be verified.",
        };
    }
  };

  // =====================================================
  // INVESTIGATION ITEM
  // =====================================================

  const InvestigationItem = ({
    icon,
    title,
    type,
  }) => {
    const information =
      getInvestigationStatus(type);

    return (
      <div
        className={`investigation-item ${information.status}`}
      >
        <div className="investigation-left">
          <div className="investigation-icon">
            {icon}
          </div>

          <div className="investigation-text">
            <strong>
              {title}
            </strong>

            <span>
              {information.description}
            </span>
          </div>
        </div>

        <div className="investigation-status">
          <div className="investigation-status-icon">
            {information.icon}
          </div>

          <span>
            {information.label}
          </span>
        </div>
      </div>
    );
  };

  // =====================================================
  // AI ANALYSIS DATA
  // =====================================================

  const aiAnalysis =
    result?.ai_decision?.ai_analysis;

  const aiExplanation =
    result?.ai_decision?.ai_explanation ||
    aiAnalysis?.explanation ||
    result?.ai_decision?.summary ||
    "No AI explanation available.";

  const detectedSignals =
    aiAnalysis?.detected ||
    result?.ai_decision?.detected ||
    [];

  const investigationFindings =
    aiAnalysis?.investigation ||
    result?.risk_analysis?.reasons ||
    [];

  const verificationSteps =
    aiAnalysis?.verification_steps ||
    result?.ai_decision?.recommended_actions ||
    [];

  const aiRecommendation =
    aiAnalysis?.recommendation ||
    result?.risk_analysis?.recommendation ||
    "Verify the payment before proceeding.";

  // =====================================================
  // DECISION HELPERS
  // =====================================================

  const riskLevel =
    result?.risk_analysis?.risk_level?.toLowerCase() || "unknown";

  const decision =
    result?.ai_decision?.decision ||
    (riskLevel === "high"
      ? "DO_NOT_PROCEED"
      : riskLevel === "medium"
      ? "VERIFY_BEFORE_PROCEEDING"
      : "LOW_RISK_BUT_VERIFY");

  const decisionTitle =
    decision === "DO_NOT_PROCEED"
      ? "Do not proceed with this payment"
      : decision === "VERIFY_BEFORE_PROCEEDING"
      ? "Verify the payment before proceeding"
      : "Low risk detected — still verify before paying";

  const decisionIcon =
    decision === "DO_NOT_PROCEED"
      ? "⛔"
      : decision === "VERIFY_BEFORE_PROCEEDING"
      ? "⚠️"
      : "🛡️";

  const defaultVerificationSteps = [
    "Confirm the recipient name and UPI ID directly with the intended person or business.",
    "Confirm the amount independently before entering your UPI PIN.",
    "Do not trust urgent payment instructions or links received in unexpected messages.",
    "If the request looks suspicious, stop and contact the organization using its official contact details.",
  ];

  const actionableVerificationSteps =
    Array.isArray(verificationSteps) && verificationSteps.length > 0
      ? verificationSteps
      : defaultVerificationSteps;

  const toggleVerificationStep = (index) => {
    setCheckedSteps((current) =>
      current.includes(index)
        ? current.filter((item) => item !== index)
        : [...current, index]
    );
  };

  const copyValue = async (value, field) => {
    if (!value) return;

    try {
      await navigator.clipboard.writeText(String(value));
      setCopiedField(field);
      setTimeout(() => setCopiedField(""), 1800);
    } catch {
      setError("The value could not be copied. Please copy it manually.");
    }
  };

  // =====================================================
  // PHASE 5.1 — VERIFICATION INTELLIGENCE
  // =====================================================

  const verification = result?.verification || {};

  const verificationChecks = Array.isArray(verification.checks)
    ? verification.checks
    : [];

  const getVerificationCheck = (field) =>
    verificationChecks.find((check) => check?.field === field) || {
      field,
      status: "missing",
      message: "No verification result was returned for this field.",
      ocr_value: null,
      qr_value: null,
    };

  const verificationStatus = verification.verification_status || "incomplete";
  const verificationConfidence =
    Number.isFinite(Number(verification.verification_confidence))
      ? Number(verification.verification_confidence)
      : 0;
  const evidenceCompleteness =
    Number.isFinite(Number(verification.evidence_completeness))
      ? Number(verification.evidence_completeness)
      : 0;
  const consistencyScore =
    Number.isFinite(Number(verification.consistency_score))
      ? Number(verification.consistency_score)
      : 0;

  const verificationRecommendation =
    verification.recommendation || "VERIFY_BEFORE_PROCEEDING";

  const verificationStatusLabel = {
    passed: "VERIFICATION PASSED",
    failed: "VERIFICATION FAILED",
    incomplete: "VERIFICATION INCOMPLETE",
    invalid_qr: "INVALID QR",
    unsupported_qr: "UNSUPPORTED QR",
  }[verificationStatus] || "VERIFICATION INCOMPLETE";

  const verificationStatusClass = [
    "passed",
    "failed",
    "incomplete",
    "invalid_qr",
    "unsupported_qr",
  ].includes(verificationStatus)
    ? verificationStatus
    : "incomplete";

  const verificationRecommendationLabel = {
    DO_NOT_PROCEED: "DO NOT PROCEED",
    VERIFY_BEFORE_PROCEEDING: "VERIFY BEFORE PROCEEDING",
    PROCEED_WITH_NORMAL_CAUTION: "PROCEED WITH NORMAL CAUTION",
  }[verificationRecommendation] || "VERIFY BEFORE PROCEEDING";

  const verificationSummary =
    Array.isArray(verification.summary) && verification.summary.length > 0
      ? verification.summary
      : ["No detailed verification summary was returned."];

  // =====================================================
  // PHASE 5.3 — ADVANCED PAYMENT INTELLIGENCE
  // =====================================================

  const paymentIntelligence =
    result?.risk_analysis?.payment_intelligence || {};

  const intelligenceAssessment =
    paymentIntelligence.assessment || "REQUIRES_REVIEW";

  const intelligenceConfidence =
    Number.isFinite(Number(paymentIntelligence.confidence))
      ? Number(paymentIntelligence.confidence)
      : 0;

  const intelligenceEvidenceQuality =
    paymentIntelligence.evidence_quality || "UNKNOWN";

  const intelligenceEvidenceCompleteness =
    Number.isFinite(Number(paymentIntelligence.evidence_completeness))
      ? Number(paymentIntelligence.evidence_completeness)
      : 0;

  const intelligenceAmountProfile =
    paymentIntelligence.amount_profile || "NOT_AVAILABLE";

  const intelligenceRecipientProfile =
    paymentIntelligence.recipient_profile || "UNIDENTIFIED";

  const intelligenceQrProfile =
    paymentIntelligence.qr_profile || "NOT_DETECTED";

  const intelligenceConsistency =
    paymentIntelligence.cross_source_consistency || "NOT_AVAILABLE";

  const intelligenceBehavior =
    paymentIntelligence.behavior_profile ||
    "NO_STRONG_BEHAVIORAL_SIGNAL";

  const intelligenceFlags =
    Array.isArray(paymentIntelligence.flags)
      ? paymentIntelligence.flags
      : [];

  const intelligenceSignals =
    Array.isArray(paymentIntelligence.active_signal_categories)
      ? paymentIntelligence.active_signal_categories
      : [];

  // =====================================================
  // PHASE 5.4 — EVIDENCE & VERIFICATION TIMELINE
  // =====================================================

  const timelineVerificationStatus =
    verification.verification_status || "incomplete";

  const timelineQrDetected =
    Boolean(result?.qr_analysis?.detected);

  const timelineOcrAvailable =
    Boolean(
      result &&
      (
        verificationChecks.some(
          (check) =>
            check?.status === "match" ||
            check?.status === "single_source"
        ) ||
        Number(evidenceCompleteness) > 0
      )
    );

  const timelineConsistencyStrong =
    Number(consistencyScore) >= 80;

  const timelineDecisionAvailable =
    Boolean(
      result?.ai_decision?.decision ||
      result?.risk_analysis?.risk_level
    );

  const evidenceTimeline = [
    {
      number: "01",
      icon: "📥",
      title: "Payment Request Detected",
      description: "CivicPay received the uploaded payment evidence.",
      status: result ? "complete" : "pending",
    },
    {
      number: "02",
      icon: "📝",
      title: "OCR Evidence Extracted",
      description: timelineOcrAvailable
        ? "Payment text was extracted from the supplied image."
        : "No readable OCR text was available.",
      status: timelineOcrAvailable ? "complete" : "warning",
    },
    {
      number: "03",
      icon: "📱",
      title: "QR Code Investigated",
      description: timelineQrDetected
        ? "A QR code was detected and its payment payload was inspected."
        : "No readable QR code was detected.",
      status: timelineQrDetected ? "complete" : "warning",
    },
    {
      number: "04",
      icon: "🔗",
      title: "Evidence Cross-Checked",
      description: timelineConsistencyStrong
        ? "Available payment sources show strong consistency."
        : "Some evidence is missing or requires additional review.",
      status: timelineConsistencyStrong ? "complete" : "warning",
    },
    {
      number: "05",
      icon: "🛡️",
      title: "Verification Completed",
      description:
        timelineVerificationStatus === "passed"
          ? "Verification checks passed for the available evidence."
          : timelineVerificationStatus === "failed"
          ? "Verification detected a conflict or invalid evidence."
          : "Verification completed with incomplete evidence.",
      status:
        timelineVerificationStatus === "passed"
          ? "complete"
          : "warning",
    },
    {
      number: "06",
      icon: "🧠",
      title: "AI Decision Generated",
      description: timelineDecisionAvailable
        ? "CivicPay generated a risk decision and recommended action."
        : "No final AI decision was returned.",
      status: timelineDecisionAvailable ? "complete" : "warning",
    },
  ];

  const timelineCompletedCount = evidenceTimeline.filter(
    (event) => event.status === "complete"
  ).length;

  // =====================================================
  // PHASE 6.5.1 — SECURITY STATUS DASHBOARD
  // =====================================================

  const currentUser = getCurrentUser();

  const securityHistoryCount = analysisHistory.length;

  const securityHighRiskCount = analysisHistory.filter(
    (item) => String(item?.risk_level || "").toUpperCase() === "HIGH"
  ).length;

  const securityMediumRiskCount = analysisHistory.filter(
    (item) => String(item?.risk_level || "").toUpperCase() === "MEDIUM"
  ).length;

  const securitySessionActive = Boolean(
    getAccessToken() && !isTokenExpired(getAccessToken())
  );

  const formatSessionRemaining = (seconds) => {
    if (!Number.isFinite(Number(seconds))) {
      return "Protected";
    }

    const safeSeconds = Math.max(0, Number(seconds));
    const hours = Math.floor(safeSeconds / 3600);
    const minutes = Math.floor((safeSeconds % 3600) / 60);
    const remainingSeconds = safeSeconds % 60;

    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }

    return `${minutes}m ${String(remainingSeconds).padStart(2, "0")}s`;
  };

  const sessionExpiryText = securitySessionActive
    ? formatSessionRemaining(sessionRemainingSeconds)
    : "Sign in required";

  const sessionProgressPercent =
    Number.isFinite(Number(sessionRemainingSeconds))
      ? Math.min(
          100,
          Math.max(
            0,
            (Number(sessionRemainingSeconds) / (60 * 60)) * 100
          )
        )
      : 100;

  // =====================================================
  // RENDER
  // =====================================================

  return (
    <div className="home">

      {/* =================================================
          NAVBAR
      ================================================= */}

      <nav className="navbar">

        <div className="logo">
          Civic<span>Pay</span>
        </div>

        <div className="nav-links">
          <a href="#how-it-works">
            How It Works
          </a>

          <a href="#analysis-history">
            History
          </a>

          <a href="#security-dashboard">
            Security
          </a>

          <a href="#about">
            About
          </a>

          {getCurrentUser() && (
            <span className="nav-user">
              👤 {getCurrentUser().username}
            </span>
          )}

          <span className="nav-security-status">
            🔐 Secure session
          </span>

          <button
            type="button"
            className="nav-logout-button"
            onClick={() => {
              logout();
              setResult(null);
              setSelectedFile(null);
              setPreview(null);
              setError("");
              window.location.href = "/login";
            }}
          >
            Logout
          </button>
        </div>

      </nav>


      {/* =================================================
          HERO SECTION
      ================================================= */}

      <main className="hero">

        <div className="hero-content">

          <div className="badge">
            🛡️ AI-Powered Payment Protection
          </div>


          <h1>
            Before You Pay,
            <br />
            <span>
              Let CivicPay Investigate.
            </span>
          </h1>


          <p className="hero-description">
            Upload a payment message, screenshot,
            or QR code. CivicPay's AI investigates
            the request and helps you decide whether
            it is safe to pay.
          </p>

          <div className="privacy-security-panel">
            <div className="privacy-security-icon">
              🔐
            </div>
            <div>
              <strong>Privacy &amp; Security Protected</strong>
              <p>
                Your image is processed temporarily for this analysis.
                CivicPay does not store the uploaded image, raw OCR text,
                or raw QR payload in your analysis history.
              </p>
            </div>
          </div>

          {sessionMessage && (
            <div className="session-security-message">
              🛡️ {sessionMessage}
            </div>
          )}

          {/* =================================================
              UPLOAD BOX
          ================================================= */}

          <div
            className="upload-box"
            id="analyze-payment"
          >

            {!selectedFile ? (
              <>

                <div className="upload-icon">
                  📄
                </div>

                <h3>
                  Analyze a Payment Request
                </h3>

                <p>
                  Upload a screenshot or image
                  containing the payment request.
                </p>

                <label className="upload-button">

                  Choose Screenshot

                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/jpg"
                    onChange={handleFileChange}
                    hidden
                  />

                </label>

                <span className="upload-note">
                  PNG, JPG or JPEG • Maximum 10 MB
                </span>

              </>
            ) : (
              <>

                <h3>
                  Screenshot Selected
                </h3>

                <div className="preview-container">

                  <img
                    src={preview}
                    alt="Payment screenshot preview"
                    className="preview-image"
                  />

                </div>

                <p className="selected-file">
                  📎 {selectedFile.name}
                </p>

                <div className="upload-actions">

                  <button
                    className="analyze-button"
                    onClick={analyzePayment}
                    disabled={loading}
                  >
                    {loading
                      ? "⏳ Analyzing..."
                      : "🔍 Analyze Payment"}
                  </button>

                  <button
                    className="remove-button"
                    onClick={removeFile}
                    disabled={loading}
                  >
                    Remove
                  </button>

                </div>

              </>
            )}

          </div>


          {/* =================================================
              ERROR
          ================================================= */}

          {error && (
            <div className="error-message">
              ⚠️ {error}
            </div>
          )}


          {/* =================================================
              PHASE 3.3 — LIVE AI ANALYSIS
          ================================================= */}

          {loading && (

            <div className="live-analysis-card">

              <div className="live-analysis-header">

                <div className="live-ai-icon">
                  ✦
                </div>

                <div>

                  <p className="live-analysis-label">
                    CIVICPAY AI
                  </p>

                  <h3>
                    Investigating Payment
                  </h3>

                  <span>
                    Please wait while CivicPay analyzes
                    the payment request.
                  </span>

                </div>

                <div className="analysis-pulse">

                  <span></span>

                  ANALYZING

                </div>

              </div>


              <div className="analysis-stage-list">

                {analysisStages.map(
                  (stage, index) => {

                    const isComplete =
                      index < analysisStep;

                    const isCurrent =
                      index === analysisStep;

                    return (
                      <div
                        key={stage.number}
                        className={`analysis-stage ${
                          isComplete
                            ? "complete"
                            : ""
                        } ${
                          isCurrent
                            ? "current"
                            : ""
                        }`}
                      >

                        <div className="stage-number">

                          {isComplete
                            ? "✓"
                            : stage.number}

                        </div>


                        <div className="stage-icon">
                          {stage.icon}
                        </div>


                        <div className="stage-content">

                          <strong>
                            {stage.title}
                          </strong>

                          <span>
                            {stage.description}
                          </span>

                        </div>


                        {isCurrent && (

                          <div className="stage-loader">

                            <span></span>
                            <span></span>
                            <span></span>

                          </div>

                        )}

                      </div>
                    );
                  }
                )}

              </div>


              <div className="analysis-progress">

                <div
                  className="analysis-progress-fill"
                  style={{
                    width: `${
                      ((analysisStep + 1) /
                        analysisStages.length) *
                      100
                    }%`,
                  }}
                ></div>

              </div>


              <p className="analysis-status-text">

                {analysisStages[
                  analysisStep
                ]?.icon}{" "}

                {analysisStages[
                  analysisStep
                ]?.title}

                {" "}stage in progress...

              </p>

            </div>

          )}

        </div>

      </main>


      {/* =================================================
          INVESTIGATION RESULT
      ================================================= */}

      {result && (

        <section
          className="result-section"
          id="investigation-result"
        >

          <div className="result-container">


            {/* =================================================
                RESULT HEADER
            ================================================= */}

            <div className="result-heading">

              <div className="result-icon">
                🔎
              </div>

              <div>

                <p className="result-label">
                  CIVICPAY AI INVESTIGATION
                </p>

                <h2>
                  Investigation Result
                </h2>

                <p>
                  Analysis completed securely.{" "}
                  <strong>
                    ID: {result.analysis_id || "Unavailable"}
                  </strong>
                </p>

              </div>

              <button
                className="new-analysis-button"
                onClick={analyzeAnother}
              >
                + New Analysis
              </button>

            </div>


            {/* =================================================
                RISK OVERVIEW
            ================================================= */}

            <div
              className={`risk-card ${getRiskClass(
                result.risk_analysis?.risk_level
              )}`}
            >

              <div className="risk-main">

                <div className="risk-shield">

                  {getRiskIcon(
                    result.risk_analysis?.risk_level
                  )}

                </div>


                <div className="risk-information">

                  <div className="risk-title-row">

                    <p className="risk-title">
                      CURRENT SECURITY LEVEL
                    </p>

                    <span className="risk-status-pill">
                      AI ASSESSMENT
                    </span>

                  </div>


                  <h3>
                    {result.risk_analysis?.risk_level ||
                      "UNKNOWN"}{" "}
                    RISK
                  </h3>


                  <p className="risk-message">
                    {getRiskMessage(
                      result.risk_analysis?.risk_level
                    )}
                  </p>


                  <span className="risk-decision-badge">

                    {result.ai_decision?.decision ===
                    "DO_NOT_PROCEED"
                      ? "⛔ DO NOT PROCEED"
                      : result.ai_decision?.decision ===
                        "VERIFY_BEFORE_PROCEEDING"
                      ? "⚠ VERIFY BEFORE PROCEEDING"
                      : "✓ VERIFY BEFORE PAYING"}

                  </span>

                </div>

              </div>


              {/* =================================================
                  ANIMATED RISK SCORE
              ================================================= */}

              <div className="risk-score-box">

                <span className="risk-score-label">
                  Risk Score
                </span>


                <div className="risk-score-number">

                  <strong>
                    {displayedRiskScore}
                  </strong>

                  <small>
                    /100
                  </small>

                </div>


                <div className="risk-progress">

                  <div
                    className="risk-progress-fill"
                    style={{
                      width: `${Math.min(
                        displayedRiskScore,
                        100
                      )}%`,
                    }}
                  ></div>

                </div>

              </div>

            </div>


            {/* =================================================
                QUICK METRICS
            ================================================= */}

            <div className="quick-metrics">

              <div className="metric-card">

                <span className="metric-icon">
                  ◈
                </span>

                <div>

                  <small>
                    Risk Score
                  </small>

                  <strong>
                    {result.risk_analysis?.risk_score ??
                      0}
                    /100
                  </strong>

                </div>

              </div>


              <div className="metric-card">

                <span className="metric-icon">
                  ✦
                </span>

                <div>

                  <small>
                    AI Confidence
                  </small>

                  <strong>
                    {result.ai_decision?.confidence ??
                      0}
                    %
                  </strong>

                </div>

              </div>


              <div className="metric-card">

                <span className="metric-icon">
                  ⌁
                </span>

                <div>

                  <small>
                    QR Status
                  </small>

                  <strong>
                    {result.qr_analysis?.detected
                      ? "Detected"
                      : "Not Detected"}
                  </strong>

                </div>

              </div>


              <div className="metric-card">

                <span className="metric-icon">
                  ◎
                </span>

                <div>

                  <small>
                    Payment Method
                  </small>

                  <strong>
                    {result.payment?.payment_method ||
                      "Unknown"}
                  </strong>

                </div>

              </div>

            </div>


            {/* =================================================
                SECURITY PIPELINE
            ================================================= */}

            <div className="security-pipeline-card">

              <div className="pipeline-header">

                <div>

                  <span className="section-label">
                    SECURITY PIPELINE
                  </span>

                  <h3>
                    How CivicPay analyzed this payment
                  </h3>

                </div>

                <span className="analysis-complete-badge">
                  ✓ ANALYSIS COMPLETE
                </span>

              </div>


              <div className="pipeline">

                {analysisStages.map(
                  (stage, index) => (

                    <div
                      className="pipeline-stage"
                      key={stage.number}
                    >

                      <div className="pipeline-number">
                        {stage.number}
                      </div>

                      <strong>
                        {stage.title}
                      </strong>

                      <span>
                        {stage.description}
                      </span>

                      {index <
                        analysisStages.length - 1 && (
                        <div className="pipeline-line"></div>
                      )}

                    </div>

                  )
                )}

              </div>

            </div>


            {/* =================================================
                DETECTED + INVESTIGATION
            ================================================= */}

            <div className="two-column-result">


              {/* =================================================
                  WHAT CIVICPAY DETECTED
              ================================================= */}

              <div className="detection-card">

                <div className="section-title">

                  <div className="section-icon">
                    ◉
                  </div>

                  <div>

                    <h3>
                      What CivicPay Detected
                    </h3>

                    <p>
                      Signals identified from the payment request
                    </p>

                  </div>

                </div>


                <div className="signal-list">

                  {detectedSignals.length > 0 ? (

                    detectedSignals.map(
                      (signal, index) => (

                        <div
                          className="signal-item"
                          key={index}
                        >

                          <span>
                            ✓
                          </span>

                          <p>
                            {signal}
                          </p>

                        </div>

                      )
                    )

                  ) : (

                    <div className="signal-item">

                      <span>
                        ✓
                      </span>

                      <p>
                        No additional detection signals
                        were reported.
                      </p>

                    </div>

                  )}

                </div>

              </div>


              {/* =================================================
                  INVESTIGATION FINDINGS
              ================================================= */}

              <div className="findings-card">

                <div className="section-title">

                  <div className="section-icon">
                    ⌕
                  </div>

                  <div>

                    <h3>
                      Investigation Findings
                    </h3>

                    <p>
                      Evidence reviewed by CivicPay
                    </p>

                  </div>

                </div>


                <div className="finding-list">

                  {investigationFindings.length > 0 ? (

                    investigationFindings.map(
                      (finding, index) => (

                        <div
                          className="finding-item"
                          key={index}
                        >

                          <span>
                            !
                          </span>

                          <p>
                            {finding}
                          </p>

                        </div>

                      )
                    )

                  ) : (

                    <div className="finding-item">

                      <span>
                        ✓
                      </span>

                      <p>
                        No investigation findings
                        were returned.
                      </p>

                    </div>

                  )}

                </div>

              </div>

            </div>


            {/* =================================================
                AI SECURITY ANALYSIS
            ================================================= */}

            <div className="ai-analysis-card">

              <div className="ai-analysis-header">

                <div className="section-icon ai-icon">
                  ✦
                </div>

                <div>

                  <span className="section-label">
                    CIVICPAY AI
                  </span>

                  <h3>
                    Security Explanation
                  </h3>

                  <p>
                    Generated using the payment evidence
                    provided to CivicPay.
                  </p>

                </div>

                <span className="ai-powered-badge">
                  Llama AI
                </span>

              </div>


              <div className="ai-explanation">

                {aiExplanation}

              </div>

            </div>


            {/* =================================================
                VERIFICATION STEPS
            ================================================= */}

            <div className={`verification-card ${riskLevel}`}>

              <div className="section-title">
                <div className="section-icon verify-icon">
                  {decisionIcon}
                </div>
                <div>
                  <h3>Verify Before Paying</h3>
                  <p>Complete these checks before taking action.</p>
                </div>
              </div>

              <div className="verification-decision">
                <div className="verification-decision-icon">
                  {decisionIcon}
                </div>
                <div>
                  <strong>{decisionTitle}</strong>
                  <span>
                    CivicPay's recommendation is based on the evidence returned by the investigation.
                  </span>
                </div>
              </div>

              <div className="verification-progress-row">
                <span>Verification progress</span>
                <strong>
                  {checkedSteps.length}/{actionableVerificationSteps.length} completed
                </strong>
              </div>

              <div className="verification-grid actionable-verification-grid">
                {actionableVerificationSteps.map((step, index) => {
                  const checked = checkedSteps.includes(index);
                  return (
                    <button
                      type="button"
                      className={`verification-item actionable ${checked ? "checked" : ""}`}
                      key={index}
                      onClick={() => toggleVerificationStep(index)}
                    >
                      <div className="verification-number">
                        {checked ? "✓" : index + 1}
                      </div>
                      <p>{step}</p>
                      <span className="verification-check-label">
                        {checked ? "Completed" : "Mark done"}
                      </span>
                    </button>
                  );
                })}
              </div>

              <div className="verification-safety-note">
                <span>🛡️</span>
                <p>
                  CivicPay does not make the payment for you. Always verify the recipient in your own trusted payment app before entering your PIN.
                </p>
              </div>

            </div>

            {/* =================================================
                RECOMMENDATION
            ================================================= */}

            <div
              className={`recommendation-card ${getRiskClass(
                result.risk_analysis?.risk_level
              )}`}
            >

              <div className="recommendation-icon">
                ⚠
              </div>

              <div className="recommendation-content">

                <div className="recommendation-heading">

                  <h3>
                    CivicPay Recommendation
                  </h3>

                  <span>
                    SECURITY ACTION
                  </span>

                </div>

                <p>
                  {aiRecommendation}
                </p>

              </div>

            </div>


            {/* =================================================
                INVESTIGATION BREAKDOWN
            ================================================= */}

            <div className="investigation-card">

              <div className="section-title">

                <div className="section-icon investigation-section-icon">
                  🧩
                </div>

                <div>

                  <h3>
                    Investigation Breakdown
                  </h3>

                  <p>
                    Key signals checked by CivicPay
                    during analysis.
                  </p>

                </div>

              </div>


              <div className="investigation-grid">

                <InvestigationItem
                  icon="💰"
                  title="Payment Amount"
                  type="amount"
                />

                <InvestigationItem
                  icon="👤"
                  title="Recipient"
                  type="recipient"
                />

                <InvestigationItem
                  icon="📱"
                  title="QR Code"
                  type="qr"
                />

                <InvestigationItem
                  icon="🆔"
                  title="Transaction ID"
                  type="transaction"
                />

                <InvestigationItem
                  icon="🔢"
                  title="UTR Number"
                  type="utr"
                />

                <InvestigationItem
                  icon="💳"
                  title="Payment Status"
                  type="status"
                />

              </div>

            </div>


            {/* =================================================
                PAYMENT DETAILS
            ================================================= */}

            <div className="details-card">

              <div className="section-title">

                <div className="section-icon">
                  💳
                </div>

                <div>

                  <h3>
                    Payment Details
                  </h3>

                  <p>
                    Information extracted from the
                    payment request.
                  </p>

                </div>

              </div>


              <div className="details-grid">

                <div className="detail-item">

                  <span className="detail-label">
                    Amount
                  </span>

                  <strong className="amount-value">

                    {result.payment?.amount !== null &&
                    result.payment?.amount !== undefined
                      ? `₹${result.payment.amount}`
                      : "Not detected"}

                  </strong>

                </div>


                <div className="detail-item">

                  <span className="detail-label">
                    Merchant / Recipient
                  </span>

                  <strong>
                    {result.payment?.merchant ||
                      "Not detected"}
                  </strong>

                </div>


                <div className="detail-item">

                  <span className="detail-label">
                    Date
                  </span>

                  <strong>
                    {result.payment?.date ||
                      "Not detected"}
                  </strong>

                </div>


                <div className="detail-item">

                  <span className="detail-label">
                    Payment Status
                  </span>

                  <strong
                    className={`status ${
                      result.payment?.payment_status ||
                      "unknown"
                    }`}
                  >
                    {result.payment?.payment_status ||
                      "Unknown"}
                  </strong>

                </div>


                <div className="detail-item full-width">

                  <span className="detail-label">
                    Payment Method
                  </span>

                  <strong>
                    {result.payment?.payment_method ||
                      "Not detected"}
                  </strong>

                </div>


                <div className="detail-item full-width">

                  <span className="detail-label">
                    Transaction ID
                  </span>

                  <div className="copy-field">
                    <strong className="transaction-id">
                      {result.payment?.transaction_id || "Not detected"}
                    </strong>
                    {result.payment?.transaction_id && (
                      <button type="button" className="copy-button" onClick={() => copyValue(result.payment.transaction_id, "transaction")}>
                        {copiedField === "transaction" ? "Copied" : "Copy"}
                      </button>
                    )}
                  </div>

                </div>


                <div className="detail-item full-width">

                  <span className="detail-label">
                    UTR
                  </span>

                  <strong>
                    {result.payment?.utr ||
                      "Not detected"}
                  </strong>

                </div>


                <div className="detail-item full-width">

                  <span className="detail-label">
                    UPI ID
                  </span>

                  <div className="copy-field">
                    <strong>
                      {result.payment?.upi_id || "Not detected"}
                    </strong>
                    {result.payment?.upi_id && (
                      <button type="button" className="copy-button" onClick={() => copyValue(result.payment.upi_id, "upi")}>
                        {copiedField === "upi" ? "Copied" : "Copy"}
                      </button>
                    )}
                  </div>

                </div>

              </div>

            </div>


            {/* =================================================
                QR ANALYSIS
            ================================================= */}

            <div className="qr-card">

              <div className="section-title">

                <div className="section-icon qr-section-icon">
                  📱
                </div>

                <div>

                  <h3>
                    QR Payment Analysis
                  </h3>

                  <p>
                    CivicPay decoded and inspected
                    the payment QR.
                  </p>

                </div>

              </div>


              <div
                className={`qr-status ${
                  result.qr_analysis?.detected
                    ? "detected"
                    : "not-detected"
                }`}
              >

                <div className="qr-status-icon">

                  {result.qr_analysis?.detected
                    ? "✓"
                    : "!"}

                </div>


                <div>

                  <strong>

                    {result.qr_analysis?.detected
                      ? "QR Code Detected"
                      : "QR Code Not Detected"}

                  </strong>

                  <p>

                    {result.qr_analysis?.detected
                      ? result.qr_analysis?.is_payment_qr
                        ? "A valid UPI payment QR was detected."
                        : "A QR code was detected, but it does not contain a valid UPI payment link."
                      : "No readable QR code was found in the uploaded image."}

                  </p>

                </div>

              </div>


              {result.risk_analysis?.qr_details && (
                <div className="qr-details-grid">
                  <div className="qr-detail-item">
                    <span className="detail-label">
                      QR Evidence
                    </span>

                    <strong>
                      Securely processed
                    </strong>
                  </div>

                  <div className="qr-detail-item">
                    <span className="detail-label">
                      Sensitive Payload
                    </span>

                    <strong>
                      Protected
                    </strong>
                  </div>

                  <div className="qr-detail-item">
                    <span className="detail-label">
                      Data Retention
                    </span>

                    <strong>
                      Not retained
                    </strong>
                  </div>
                </div>
              )}

            </div>


            {/* =================================================
                PHASE 5.1 — VERIFICATION INTELLIGENCE
            ================================================= */}

            <div className={`verification-intelligence-card ${verificationStatusClass}`}>

              <div className="section-title">

                <div className="section-icon verification-intelligence-icon">
                  🛡️
                </div>

                <div>
                  <span className="phase-label">
                    PHASE 5.1
                  </span>

                  <h3>
                    Verification Intelligence
                  </h3>

                  <p>
                    CivicPay cross-checks payment evidence from OCR and the QR code.
                  </p>
                </div>

              </div>


              <div className="verification-intelligence-status">

                <div>
                  <span className="verification-status-label">
                    VERIFICATION STATUS
                  </span>

                  <strong>
                    {verificationStatusLabel}
                  </strong>
                </div>

                <div className="verification-confidence-badge">
                  <span>Confidence</span>
                  <strong>{verificationConfidence}%</strong>
                </div>

              </div>


              <div className="verification-metrics-grid">

                <div className="verification-metric">
                  <span>Evidence Completeness</span>
                  <strong>{evidenceCompleteness}%</strong>

                  <div className="verification-meter">
                    <span style={{ width: `${Math.min(100, Math.max(0, evidenceCompleteness))}%` }} />
                  </div>
                </div>

                <div className="verification-metric">
                  <span>Consistency Score</span>
                  <strong>{consistencyScore}%</strong>

                  <div className="verification-meter">
                    <span style={{ width: `${Math.min(100, Math.max(0, consistencyScore))}%` }} />
                  </div>
                </div>

                <div className="verification-metric">
                  <span>Verification Confidence</span>
                  <strong>{verificationConfidence}%</strong>

                  <div className="verification-meter">
                    <span style={{ width: `${Math.min(100, Math.max(0, verificationConfidence))}%` }} />
                  </div>
                </div>

              </div>


              <div className="verification-intelligence-grid">

                {[
                  ["upi_id", "🆔", "UPI ID"],
                  ["merchant", "👤", "Recipient"],
                  ["amount", "₹", "Amount"],
                  ["payment_method", "💳", "Payment Method"],
                ].map(([field, icon, label]) => {

                  const check = getVerificationCheck(field);

                  const statusText = {
                    match: "MATCH",
                    mismatch: "MISMATCH",
                    missing: "MISSING",
                    single_source: "SINGLE SOURCE",
                  }[check.status] || "UNAVAILABLE";

                  return (
                    <div
                      className={`verification-intelligence-item ${check.status}`}
                      key={field}
                    >

                      <div className="verification-item-heading">

                        <span className="verification-item-icon">
                          {icon}
                        </span>

                        <span>
                          {label}
                        </span>

                      </div>

                      <strong className="verification-item-status">
                        {check.status === "match"
                          ? "✓ "
                          : check.status === "mismatch"
                          ? "✕ "
                          : check.status === "single_source"
                          ? "• "
                          : "! "}
                        {statusText}
                      </strong>

                      <p>
                        {check.message || "No additional information available."}
                      </p>

                      {(check.ocr_value || check.qr_value) && (
                        <div className="verification-values">
                          <span>
                            🔐 Sensitive source values are hidden for privacy.
                          </span>
                        </div>
                      )}

                    </div>
                  );
                })}

              </div>


              <div className="verification-summary-box">

                <div className="verification-summary-heading">
                  <span>🔎</span>
                  <strong>Verification Findings</strong>
                </div>

                <ul>
                  {verificationSummary.map((item, index) => (
                    <li key={index}>
                      {item}
                    </li>
                  ))}
                </ul>

              </div>


              <div className={`verification-recommendation ${verificationRecommendation === "DO_NOT_PROCEED" ? "danger" : verificationRecommendation === "PROCEED_WITH_NORMAL_CAUTION" ? "safe" : "warning"}`}>

                <div className="verification-recommendation-icon">
                  {verificationRecommendation === "DO_NOT_PROCEED"
                    ? "⛔"
                    : verificationRecommendation === "PROCEED_WITH_NORMAL_CAUTION"
                    ? "✓"
                    : "⚠️"}
                </div>

                <div>
                  <span>RECOMMENDED ACTION</span>
                  <strong>
                    {verificationRecommendationLabel}
                  </strong>
                </div>

              </div>


              <div className="verification-scope-note">
                <span>ℹ️</span>
                <p>
                  {verification.verification_scope ||
                    "Evidence-based verification only. CivicPay does not directly verify with a bank or UPI network."}
                </p>
              </div>

            </div>


            {/* =================================================
                PHASE 5.3 — ADVANCED PAYMENT INTELLIGENCE
            ================================================= */}

            <div className={`payment-intelligence-card ${intelligenceAssessment.toLowerCase()}`}>

              <div className="section-title">
                <div className="section-icon payment-intelligence-icon">
                  🧠
                </div>

                <div>
                  <span className="phase-label">
                    PHASE 5.3
                  </span>

                  <h3>
                    Advanced Payment Intelligence
                  </h3>

                  <p>
                    CivicPay builds an evidence-based profile from payment, QR, and behavioral signals.
                  </p>
                </div>
              </div>

              <div className="payment-intelligence-summary">
                <div>
                  <span className="intelligence-label">
                    INTELLIGENCE ASSESSMENT
                  </span>
                  <strong>
                    {intelligenceAssessment.replaceAll("_", " ")}
                  </strong>
                  <p>
                    Based on the evidence available in this payment request.
                  </p>
                </div>

                <div className="intelligence-confidence">
                  <span>Evidence Confidence</span>
                  <strong>{intelligenceConfidence}%</strong>
                </div>
              </div>

              <div className="payment-intelligence-metrics">
                <div className="intelligence-metric">
                  <span>Evidence Quality</span>
                  <strong>{intelligenceEvidenceQuality}</strong>
                  <small>{intelligenceEvidenceCompleteness}% complete</small>
                </div>

                <div className="intelligence-metric">
                  <span>Amount Profile</span>
                  <strong>{intelligenceAmountProfile.replaceAll("_", " ")}</strong>
                  <small>Payment value profile</small>
                </div>

                <div className="intelligence-metric">
                  <span>Recipient Profile</span>
                  <strong>{intelligenceRecipientProfile.replaceAll("_", " ")}</strong>
                  <small>Destination evidence</small>
                </div>

                <div className="intelligence-metric">
                  <span>QR Profile</span>
                  <strong>{intelligenceQrProfile.replaceAll("_", " ")}</strong>
                  <small>QR evidence quality</small>
                </div>

                <div className="intelligence-metric">
                  <span>Consistency</span>
                  <strong>{intelligenceConsistency.replaceAll("_", " ")}</strong>
                  <small>Cross-source comparison</small>
                </div>

                <div className="intelligence-metric">
                  <span>Behavior</span>
                  <strong>{intelligenceBehavior.replaceAll("_", " ")}</strong>
                  <small>Request behavior profile</small>
                </div>
              </div>

              <div className="payment-intelligence-columns">

                <div className="intelligence-panel">
                  <div className="intelligence-panel-heading">
                    <span>🔎</span>
                    <strong>Intelligence Signals</strong>
                  </div>

                  {intelligenceSignals.length > 0 ? (
                    <div className="intelligence-chip-list">
                      {intelligenceSignals.map((signal, index) => (
                        <span className="intelligence-chip" key={index}>
                          {signal.replaceAll("_", " ")}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="intelligence-empty">
                      No strong behavioral signal was detected.
                    </p>
                  )}
                </div>

                <div className="intelligence-panel">
                  <div className="intelligence-panel-heading">
                    <span>⚠️</span>
                    <strong>Intelligence Flags</strong>
                  </div>

                  {intelligenceFlags.length > 0 ? (
                    <ul className="intelligence-flag-list">
                      {intelligenceFlags.map((flag, index) => (
                        <li key={index}>
                          {flag}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="intelligence-empty">
                      No additional intelligence flags were generated.
                    </p>
                  )}
                </div>

              </div>

              <div className="intelligence-scope-note">
                <span>ℹ️</span>
                <p>
                  {paymentIntelligence.scope ||
                    "Evidence-based payment intelligence only. CivicPay does not directly confirm bank or UPI network status."}
                </p>
              </div>

            </div>


            {/* =================================================
                PHASE 5.4 — EVIDENCE & VERIFICATION TIMELINE
            ================================================= */}

            <div className="evidence-timeline-card">

              <div className="section-title">
                <div className="section-icon evidence-timeline-icon">
                  🧭
                </div>

                <div>
                  <span className="phase-label">
                    PHASE 5.4
                  </span>

                  <h3>
                    Evidence &amp; Verification Timeline
                  </h3>

                  <p>
                    Follow the evidence path CivicPay used to reach its recommendation.
                  </p>
                </div>

                <div className="timeline-completion-badge">
                  {timelineCompletedCount}/{evidenceTimeline.length} COMPLETE
                </div>
              </div>

              <div className="evidence-timeline">

                {evidenceTimeline.map((event, index) => (
                  <div
                    className={`timeline-event ${event.status}`}
                    key={event.number}
                  >

                    <div className="timeline-marker-column">

                      <div className="timeline-marker">
                        {event.status === "complete"
                          ? "✓"
                          : event.status === "warning"
                          ? "!"
                          : event.number}
                      </div>

                      {index < evidenceTimeline.length - 1 && (
                        <div className="timeline-connector"></div>
                      )}

                    </div>

                    <div className="timeline-event-content">

                      <div className="timeline-event-header">

                        <div className="timeline-event-title">
                          <span className="timeline-event-icon">
                            {event.icon}
                          </span>

                          <div>
                            <span className="timeline-event-number">
                              STEP {event.number}
                            </span>

                            <strong>
                              {event.title}
                            </strong>
                          </div>
                        </div>

                        <span className="timeline-event-status">
                          {event.status === "complete"
                            ? "COMPLETE"
                            : event.status === "warning"
                            ? "REVIEW"
                            : "PENDING"}
                        </span>

                      </div>

                      <p>
                        {event.description}
                      </p>

                    </div>

                  </div>
                ))}

              </div>

              <div className="timeline-summary">

                <div className="timeline-summary-icon">
                  {timelineCompletedCount === evidenceTimeline.length
                    ? "✓"
                    : "ℹ️"}
                </div>

                <div>
                  <span>VERIFICATION JOURNEY</span>

                  <strong>
                    {timelineCompletedCount === evidenceTimeline.length
                      ? "Evidence path completed"
                      : "Evidence path completed with review items"}
                  </strong>

                  <p>
                    This timeline describes CivicPay's analysis process.
                    It does not represent direct bank or UPI-network confirmation.
                  </p>
                </div>

              </div>

            </div>


            {/* =================================================
                WHY THIS RESULT
            ================================================= */}

            <div className="reasons-card">

              <div className="section-title">

                <div className="section-icon brain-icon">
                  🧠
                </div>

                <div>

                  <h3>
                    Why CivicPay gave this result
                  </h3>

                  <p>
                    Security signals considered
                    during the investigation.
                  </p>

                </div>

              </div>


              <div className="reason-list">

                {result.risk_analysis?.reasons?.length > 0 ? (

                  result.risk_analysis.reasons.map(
                    (reason, index) => (

                      <div
                        className="reason-item"
                        key={index}
                      >

                        <div className="reason-number">
                          {String(index + 1).padStart(
                            2,
                            "0"
                          )}
                        </div>

                        <div className="reason-check">
                          !
                        </div>

                        <p>
                          {reason}
                        </p>

                      </div>

                    )
                  )

                ) : (

                  <div className="reason-item">

                    <div className="reason-number">
                      01
                    </div>

                    <div className="reason-check">
                      ✓
                    </div>

                    <p>
                      No specific risk reasons
                      were returned.
                    </p>

                  </div>

                )}

              </div>

            </div>


            {/* =================================================
                OCR EVIDENCE
            ================================================= */}

            <details className="ocr-card">

  <summary>

    <div className="ocr-summary-left">

      <div className="ocr-icon">
        🔐
      </div>

      <div>

        <strong>
          OCR Evidence
        </strong>

        <span>
          Sensitive extracted text is protected for privacy.
        </span>

      </div>

    </div>

    <span className="ocr-arrow">
      ↓
    </span>

  </summary>

  <div className="ocr-text">

    <div className="privacy-ocr-message">

      <strong>
        🔐 Sensitive OCR Protected
      </strong>

      <p>
        CivicPay uses extracted text internally during
        the security investigation, but raw OCR text is
        not displayed here to protect your payment
        information.
      </p>

    </div>

  </div>

</details>


            {/* =================================================
                ANALYZE ANOTHER
            ================================================= */}

            <button
              className="another-button"
              onClick={analyzeAnother}
            >

              <span>
                🔄
              </span>

              Analyze Another Payment

            </button>

          </div>

        </section>

      )}


      {/* =================================================
          PHASE 6.4.3 — ANALYSIS HISTORY
      ================================================= */}

      <section
        className="analysis-history-section"
        id="analysis-history"
      >

        <div className="section-header">
          <span className="small-badge">
            SECURE HISTORY
          </span>

          <h2>
            Your Analysis History
          </h2>

          <p>
            Review your previous CivicPay security checks.
            Only privacy-safe analysis summaries are shown here.
          </p>
        </div>

        <div className="history-security-note">
          <span className="history-security-icon">🔐</span>
          <div>
            <strong>Privacy-safe history</strong>
            <p>
              Uploaded images, raw OCR text, QR payloads and sensitive
              payment evidence are not displayed in your history.
            </p>
          </div>
        </div>

        {historyLoading ? (
          <div className="history-state-card">
            <div className="history-state-icon">⏳</div>
            <strong>Loading secure history...</strong>
            <span>Retrieving your saved analysis summaries.</span>
          </div>
        ) : historyError ? (
          <div className="history-state-card history-error-state">
            <div className="history-state-icon">⚠️</div>
            <strong>History could not be loaded</strong>
            <span>{historyError}</span>
            <button
              type="button"
              className="history-retry-button"
              onClick={fetchAnalysisHistory}
            >
              Retry
            </button>
          </div>
        ) : analysisHistory.length === 0 ? (
          <div className="history-state-card">
            <div className="history-state-icon">🛡️</div>
            <strong>No analysis history yet</strong>
            <span>
              Your completed CivicPay security checks will appear here.
            </span>
            <a
              href="#analyze-payment"
              className="history-start-button"
            >
              Analyze a Payment
            </a>
          </div>
        ) : (
          <div className="history-list">
            {analysisHistory.map((item) => (
              <article
                className="history-card"
                key={item.analysis_id}
              >
                <div className="history-card-main">
                  <div className="history-card-icon">
                    {getHistoryRiskIcon(item.risk_level)}
                  </div>

                  <div className="history-card-content">
                    <div className="history-card-topline">
                      <span className="history-card-label">
                        ANALYSIS ID
                      </span>
                      <code>{item.analysis_id}</code>
                    </div>

                    <div className="history-card-date">
                      🕒 {formatHistoryDate(item.created_at)}
                    </div>
                  </div>
                </div>

                <div
                  className={`history-risk-badge ${getHistoryRiskClass(
                    item.risk_level
                  )}`}
                >
                  {item.risk_level}
                </div>

                <div className="history-metrics">
                  <div className="history-metric">
                    <span>Risk Score</span>
                    <strong>{item.risk_score}/100</strong>
                  </div>

                  <div className="history-metric">
                    <span>Verification</span>
                    <strong>
                      {item.verification_status}
                    </strong>
                  </div>

                  <div className="history-metric">
                    <span>Confidence</span>
                    <strong>
                      {item.verification_confidence}%
                    </strong>
                  </div>

                  <div className="history-metric history-decision">
                    <span>AI Decision</span>
                    <strong>
                      {item.ai_decision}
                    </strong>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}

      </section>


      {/* =================================================
          PHASE 6.5.1 — SECURITY STATUS DASHBOARD
      ================================================= */}

      <section
        className="security-dashboard-section"
        id="security-dashboard"
      >
        <div className="section-header">
          <span className="small-badge">
            SECURITY CENTER
          </span>

          <h2>
            Your CivicPay Security Status
          </h2>

          <p>
            A clear overview of the protections active on your
            CivicPay account and payment analysis session.
          </p>
        </div>

        <div className="security-dashboard-card">
          <div className="security-dashboard-header">
            <div className="security-dashboard-identity">
              <div className="security-dashboard-icon">
                🔐
              </div>

              <div>
                <span className="security-dashboard-eyebrow">
                  ACCOUNT SECURITY
                </span>
                <h3>
                  {currentUser?.username || "Authenticated User"}
                </h3>
                <p>
                  Your CivicPay account is protected by authenticated access.
                </p>
              </div>
            </div>

            <div
              className={`security-session-badge ${
                securitySessionActive ? "active" : "inactive"
              }`}
            >
              <span className="security-session-dot" />
              {securitySessionActive
                ? "SESSION ACTIVE"
                : "SESSION CHECK REQUIRED"}
            </div>
          </div>

          {/* =================================================
              PHASE 6.5.2 — SESSION SECURITY PANEL
          ================================================= */}

          <div className="session-security-panel">
            <div className="session-security-panel-header">
              <div className="session-security-panel-title">
                <div className="session-security-panel-icon">
                  ⏱️
                </div>
                <div>
                  <span>SESSION SECURITY</span>
                  <h4>Active Session Protection</h4>
                </div>
              </div>

              <div
                className={`session-security-state ${
                  securitySessionActive ? "active" : "inactive"
                }`}
              >
                <span className="session-security-state-dot" />
                {securitySessionActive
                  ? "PROTECTED"
                  : "CHECK REQUIRED"}
              </div>
            </div>

            <div className="session-security-grid">
              <div className="session-security-stat">
                <span>SESSION STATUS</span>
                <strong>
                  {securitySessionActive
                    ? "ACTIVE"
                    : "INACTIVE"}
                </strong>
                <small>
                  {securitySessionActive
                    ? "Authenticated access is enabled."
                    : "A valid session is required."}
                </small>
              </div>

              <div className="session-security-stat">
                <span>TIME REMAINING</span>
                <strong>{sessionExpiryText}</strong>
                <small>
                  Automatic expiry monitoring is active.
                </small>
              </div>

              <div className="session-security-stat">
                <span>MONITORING</span>
                <strong>LIVE</strong>
                <small>
                  CivicPay checks the session continuously.
                </small>
              </div>
            </div>

            <div className="session-security-progress">
              <div className="session-security-progress-label">
                <span>Session validity window</span>
                <strong>
                  {securitySessionActive
                    ? `${Math.round(sessionProgressPercent)}%`
                    : "0%"}
                </strong>
              </div>

              <div className="session-security-progress-track">
                <div
                  className={`session-security-progress-fill ${
                    securitySessionActive ? "active" : "inactive"
                  }`}
                  style={{
                    width: `${
                      securitySessionActive
                        ? sessionProgressPercent
                        : 0
                    }%`,
                  }}
                />
              </div>
            </div>

            <div className="session-security-protections">
              <span>✓ Token protected</span>
              <span>✓ Expiry monitored</span>
              <span>✓ Automatic logout</span>
              <span>✓ Protected API access</span>
            </div>

            <div className="session-security-note">
              <span>🔐</span>
              <p>
                Your access token is used only to maintain your
                authenticated CivicPay session. When the session
                expires, CivicPay automatically signs you out and
                returns you to the login page.
              </p>
            </div>
          </div>

          {/* =================================================
              PHASE 6.5.3 — ACCOUNT SECURITY INFORMATION
          ================================================= */}

          <div className="account-security-panel">
            <div className="account-security-header">
              <div className="account-security-title">
                <div className="account-security-icon">👤</div>
                <div>
                  <span>ACCOUNT SECURITY</span>
                  <h4>Account Security Information</h4>
                </div>
              </div>

              <div className="account-security-badge">
                <span>✓</span> SECURE
              </div>
            </div>

            <div className="account-security-grid">
              <div className="account-security-item">
                <span>USERNAME</span>
                <strong>{currentUser?.username || "Protected account"}</strong>
                <small>Signed-in CivicPay account</small>
              </div>

              <div className="account-security-item">
                <span>EMAIL</span>
                <strong>{currentUser?.email || "Protected"}</strong>
                <small>Account contact information</small>
              </div>

              <div className="account-security-item">
                <span>AUTHENTICATION</span>
                <strong>JWT + BEARER</strong>
                <small>Protected API authentication</small>
              </div>

              <div className="account-security-item">
                <span>PASSWORD STORAGE</span>
                <strong>ARGON2 PROTECTED</strong>
                <small>Password is never shown in the dashboard</small>
              </div>

              <div className="account-security-item">
                <span>SESSION</span>
                <strong>{securitySessionActive ? "ACTIVE" : "INACTIVE"}</strong>
                <small>Automatic session expiry protection</small>
              </div>

              <div className="account-security-item">
                <span>PRIVACY MODE</span>
                <strong>ENABLED</strong>
                <small>Sensitive payment evidence is protected</small>
              </div>
            </div>

            <div className="account-security-protections">
              <span>✓ Password hash protected</span>
              <span>✓ Access token protected</span>
              <span>✓ User data isolated</span>
              <span>✓ Sensitive data hidden</span>
            </div>

            <div className="account-security-note">
              <span>🔒</span>
              <p>
                CivicPay displays only account-level security information here.
                Passwords, JWT tokens and sensitive payment details are never
                displayed as account security information.
              </p>
            </div>
          </div>

          <div className="security-status-grid">
            <div className="security-status-item">
              <div className="security-status-item-icon">✓</div>
              <div>
                <strong>Authentication</strong>
                <span>Protected access</span>
              </div>
              <b>SECURE</b>
            </div>

            <div className="security-status-item">
              <div className="security-status-item-icon">🛡️</div>
              <div>
                <strong>Analysis API</strong>
                <span>Authenticated requests</span>
              </div>
              <b>PROTECTED</b>
            </div>

            <div className="security-status-item">
              <div className="security-status-item-icon">🔒</div>
              <div>
                <strong>Analysis History</strong>
                <span>User-specific records</span>
              </div>
              <b>PRIVATE</b>
            </div>

            <div className="security-status-item">
              <div className="security-status-item-icon">🧹</div>
              <div>
                <strong>Uploaded Images</strong>
                <span>Temporary processing</span>
              </div>
              <b>NOT STORED</b>
            </div>

            <div className="security-status-item">
              <div className="security-status-item-icon">🔐</div>
              <div>
                <strong>Sensitive Evidence</strong>
                <span>Privacy-safe responses</span>
              </div>
              <b>PROTECTED</b>
            </div>

            <div className="security-status-item">
              <div className="security-status-item-icon">⏱️</div>
              <div>
                <strong>Session Protection</strong>
                <span>Automatic expiry checks</span>
              </div>
              <b>ACTIVE</b>
            </div>
          </div>

          <div className="security-dashboard-metrics">
            <div className="security-dashboard-metric">
              <span>ANALYSES</span>
              <strong>{securityHistoryCount}</strong>
              <small>Saved summaries</small>
            </div>

            <div className="security-dashboard-metric">
              <span>HIGH RISK</span>
              <strong>{securityHighRiskCount}</strong>
              <small>History records</small>
            </div>

            <div className="security-dashboard-metric">
              <span>MEDIUM RISK</span>
              <strong>{securityMediumRiskCount}</strong>
              <small>History records</small>
            </div>

            <div className="security-dashboard-metric security-dashboard-metric-status">
              <span>DATA MODE</span>
              <strong>PRIVATE</strong>
              <small>Privacy-safe history</small>
            </div>
          </div>

          {/* =================================================
              PHASE 6.5.4 — SECURITY ACTIVITY SUMMARY
          ================================================= */}

          <div className="security-activity-panel">
            <div className="security-activity-header">
              <div className="security-activity-title">
                <div className="security-activity-icon">📊</div>
                <div>
                  <span>SECURITY ACTIVITY</span>
                  <h4>Recent Security Activity Summary</h4>
                </div>
              </div>
              <div className="security-activity-live">
                <span className="security-activity-live-dot" />
                LIVE SUMMARY
              </div>
            </div>

            <div className="security-activity-grid">
              <div className="security-activity-stat">
                <span>AUTHENTICATION</span>
                <strong>{securitySessionActive ? "SUCCESSFUL" : "REQUIRED"}</strong>
                <small>{securitySessionActive ? "Current account session is authenticated." : "Sign in to access CivicPay securely."}</small>
              </div>

              <div className="security-activity-stat">
                <span>ANALYSIS ACTIVITY</span>
                <strong>{securityHistoryCount > 0 ? `${securityHistoryCount} CHECK${securityHistoryCount === 1 ? "" : "S"}` : "NO CHECKS"}</strong>
                <small>Privacy-safe analysis summaries associated with this account.</small>
              </div>

              <div className="security-activity-stat">
                <span>RISK MONITORING</span>
                <strong>{securityHighRiskCount > 0 ? "ATTENTION" : securityMediumRiskCount > 0 ? "MONITORED" : "NORMAL"}</strong>
                <small>{securityHighRiskCount > 0 ? `${securityHighRiskCount} high-risk record${securityHighRiskCount === 1 ? "" : "s"} detected.` : securityMediumRiskCount > 0 ? `${securityMediumRiskCount} medium-risk record${securityMediumRiskCount === 1 ? "" : "s"} monitored.` : "No high or medium-risk records in saved history."}</small>
              </div>
            </div>

            <div className="security-activity-recent">
              <div className="security-activity-recent-heading">
                <span>RECENT ACTIVITY</span>
                <small>Latest privacy-safe events</small>
              </div>

              {analysisHistory.length > 0 ? (
                <div className="security-activity-list">
                  {analysisHistory.slice(0, 3).map((item) => (
                    <div className="security-activity-row" key={`activity-${item.analysis_id}`}>
                      <div className="security-activity-row-icon">
                        {getHistoryRiskIcon(item.risk_level)}
                      </div>
                      <div className="security-activity-row-content">
                        <strong>Payment security check completed</strong>
                        <span>Analysis {item.analysis_id}</span>
                      </div>
                      <div className={`security-activity-row-risk ${getHistoryRiskClass(item.risk_level)}`}>
                        {item.risk_level || "UNKNOWN"}
                      </div>
                      <time>{formatHistoryDate(item.created_at)}</time>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="security-activity-empty">
                  <span>🛡️</span>
                  <div>
                    <strong>No security activity yet</strong>
                    <small>Your completed CivicPay checks will appear here.</small>
                  </div>
                </div>
              )}
            </div>

            <div className="security-activity-protections">
              <span>✓ Authentication monitored</span>
              <span>✓ Risk activity summarized</span>
              <span>✓ User history isolated</span>
              <span>✓ Sensitive details hidden</span>
            </div>
          </div>

          <div className="security-dashboard-note">
            <span>ℹ️</span>
            <p>
              CivicPay shows security status and safe analysis summaries here.
              Passwords, access tokens, raw OCR text, QR payloads and other
              sensitive payment evidence are not displayed in this dashboard.
            </p>
          </div>
        </div>
      </section>


      {/* =================================================
          FEATURES
      ================================================= */}

      <section
        className="features"
        id="how-it-works"
      >

        <div className="section-header">

          <span className="small-badge">
            HOW CIVICPAY WORKS
          </span>

          <h2>
            What CivicPay Investigates
          </h2>

          <p>
            Multiple layers of analysis help you
            understand a payment request before you pay.
          </p>

        </div>


        <div className="feature-grid">


          <div className="feature-card">

            <div className="feature-icon">
              🔍
            </div>

            <h3>
              Detect
            </h3>

            <p>
              Identifies suspicious language,
              payment requests and risk signals.
            </p>

          </div>


          <div className="feature-card">

            <div className="feature-icon">
              🕵️
            </div>

            <h3>
              Investigate
            </h3>

            <p>
              Examines the sender, merchant,
              amount and payment destination.
            </p>

          </div>


          <div className="feature-card">

            <div className="feature-icon">
              🤖
            </div>

            <h3>
              Explain
            </h3>

            <p>
              Clearly explains why a payment
              request may be risky.
            </p>

          </div>


          <div className="feature-card">

            <div className="feature-icon">
              🛡️
            </div>

            <h3>
              Recommend
            </h3>

            <p>
              Gives you a safer action to take
              before you pay.
            </p>

          </div>

        </div>

      </section>


      {/* =================================================
          ABOUT
      ================================================= */}

      <section
        className="about"
        id="about"
      >

        <div className="about-content">

          <span className="small-badge">
            ABOUT CIVICPAY
          </span>

          <h2>
            Don't just pay.
            <br />
            <span>
              Investigate first.
            </span>
          </h2>

          <p>
            CivicPay is an AI-powered payment
            protection system designed to investigate
            payment requests before you make a payment.
          </p>

        </div>

      </section>


      {/* =================================================
          FOOTER
      ================================================= */}

      <footer className="footer">

        <div className="logo">
          Civic<span>Pay</span>
        </div>

        <p>
          AI-powered payment protection.
        </p>

      </footer>

    </div>
  );
}

export default Home;