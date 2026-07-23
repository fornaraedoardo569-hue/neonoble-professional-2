import React, { useEffect, useState, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { onboardingApi } from '../api';
import { toast } from 'sonner';
import {
  Coins, ShieldCheck, FileText, Camera, ArrowRight, ArrowLeft,
  CheckCircle2, Clock, AlertTriangle, Loader2, Upload,
} from 'lucide-react';

const STEPS = ['Personal Info', 'ID Document', 'Selfie', 'Status'];

const STATUS_META = {
  NOT_STARTED: { label: 'Not started', color: 'bg-gray-500/20 text-gray-300', icon: AlertTriangle },
  PENDING: { label: 'Pending — upload your documents', color: 'bg-yellow-500/20 text-yellow-300', icon: Clock },
  IN_REVIEW: { label: 'Under review by our compliance team', color: 'bg-blue-500/20 text-blue-300', icon: Clock },
  APPROVED: { label: 'Approved — you are KYC-verified', color: 'bg-emerald-500/20 text-emerald-300', icon: CheckCircle2 },
  REJECTED: { label: 'Rejected — please contact support', color: 'bg-red-500/20 text-red-300', icon: AlertTriangle },
  ON_HOLD: { label: 'On hold — further documents needed', color: 'bg-orange-500/20 text-orange-300', icon: AlertTriangle },
};

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => {
      const result = String(r.result || '');
      const idx = result.indexOf(',');
      resolve({ b64: idx >= 0 ? result.slice(idx + 1) : result, mime: file.type });
    };
    r.onerror = reject;
    r.readAsDataURL(file);
  });
}

export default function Onboarding() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [kyc, setKyc] = useState(null);
  const [step, setStep] = useState(0);
  const [form, setForm] = useState({
    full_name: '', date_of_birth: '', nationality: 'IT',
    country_of_residence: 'IT', document_type: 'ID_CARD',
    wallet_address: '',
  });
  const idFrontRef = useRef(null);
  const idBackRef = useRef(null);
  const selfieRef = useRef(null);
  const [uploaded, setUploaded] = useState({ ID_FRONT: false, ID_BACK: false, SELFIE: false });

  useEffect(() => {
    (async () => {
      try {
        const data = await onboardingApi.myKyc();
        setKyc(data);
        // If already submitted, jump to status view
        if (data?.status && data.status !== 'NOT_STARTED') {
          setStep(3);
        }
      } catch (e) {
        console.error('Failed to load KYC status', e);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const startKyc = async () => {
    if (!form.full_name || !form.date_of_birth) {
      toast.error('Please fill in your full name and date of birth.');
      return;
    }
    setSubmitting(true);
    try {
      await onboardingApi.startKyc(form);
      const refreshed = await onboardingApi.myKyc();
      setKyc(refreshed);
      setStep(1);
      toast.success('KYC initiated. Now upload your ID document.');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to start KYC');
    } finally {
      setSubmitting(false);
    }
  };

  const upload = async (docType, file) => {
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      toast.error('File must be smaller than 5 MB.');
      return;
    }
    setSubmitting(true);
    try {
      const { b64, mime } = await readFileAsBase64(file);
      await onboardingApi.uploadDocument({ doc_type: docType, document_b64: b64, mime });
      setUploaded((u) => ({ ...u, [docType]: true }));
      toast.success(`${docType.replace('_', ' ').toLowerCase()} uploaded`);
      // Auto-refresh status
      const refreshed = await onboardingApi.myKyc();
      setKyc(refreshed);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Upload failed');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <Loader2 className="h-10 w-10 animate-spin text-purple-400" />
      </div>
    );
  }

  const status = kyc?.status || 'NOT_STARTED';
  const meta = STATUS_META[status] || STATUS_META.NOT_STARTED;
  const StatusIcon = meta.icon;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900" data-testid="onboarding-page">
      <header className="border-b border-white/10 backdrop-blur-lg">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center space-x-2">
            <Coins className="h-7 w-7 text-purple-400" />
            <span className="text-lg font-bold text-white">NeoNoble Ramp</span>
          </Link>
          <button
            onClick={() => navigate('/dashboard')}
            className="text-gray-300 hover:text-white text-sm"
            data-testid="onboarding-back-to-dashboard"
          >
            Back to Dashboard
          </button>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <ShieldCheck className="h-8 w-8 text-purple-400" />
            Identity Verification
          </h1>
          <p className="text-gray-400 mt-2">
            We need to verify your identity to comply with MiCAR &amp; AML regulations
            before you can trade. This usually takes 1–2 business days.
          </p>
        </div>

        {/* Status pill */}
        <div className={`rounded-xl p-4 mb-8 flex items-center gap-3 ${meta.color}`} data-testid="kyc-status-pill">
          <StatusIcon className="h-5 w-5" />
          <span className="font-medium">{meta.label}</span>
          {kyc?.id && (
            <span className="ml-auto text-xs opacity-70 font-mono">ref: {kyc.id.slice(0, 8)}</span>
          )}
        </div>

        {/* Stepper */}
        <div className="flex items-center justify-between mb-8">
          {STEPS.map((label, idx) => (
            <div key={label} className="flex-1 flex items-center" data-testid={`stepper-${idx}`}>
              <div className={`h-9 w-9 rounded-full flex items-center justify-center text-sm font-bold ${
                idx < step ? 'bg-emerald-500 text-white' :
                idx === step ? 'bg-purple-500 text-white' :
                'bg-white/10 text-gray-400'
              }`}>
                {idx < step ? <CheckCircle2 className="h-5 w-5" /> : idx + 1}
              </div>
              <span className={`ml-2 text-xs hidden sm:block ${idx <= step ? 'text-white' : 'text-gray-500'}`}>{label}</span>
              {idx < STEPS.length - 1 && <div className={`flex-1 h-0.5 mx-2 ${idx < step ? 'bg-emerald-500' : 'bg-white/10'}`} />}
            </div>
          ))}
        </div>

        {/* Step 0 — Personal info */}
        {step === 0 && (
          <div className="bg-white/5 backdrop-blur rounded-2xl p-6 border border-white/10" data-testid="step-personal-info">
            <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <FileText className="h-5 w-5 text-purple-400" /> Personal Information
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Full legal name" required>
                <input type="text" data-testid="onboarding-input-full-name"
                  value={form.full_name}
                  onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white" />
              </Field>
              <Field label="Date of birth" required>
                <input type="date" data-testid="onboarding-input-dob"
                  value={form.date_of_birth}
                  onChange={(e) => setForm({ ...form, date_of_birth: e.target.value })}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white" />
              </Field>
              <Field label="Nationality (ISO code)">
                <input type="text" maxLength={2} data-testid="onboarding-input-nationality"
                  value={form.nationality}
                  onChange={(e) => setForm({ ...form, nationality: e.target.value.toUpperCase() })}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white" />
              </Field>
              <Field label="Country of residence">
                <input type="text" maxLength={2} data-testid="onboarding-input-residence"
                  value={form.country_of_residence}
                  onChange={(e) => setForm({ ...form, country_of_residence: e.target.value.toUpperCase() })}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white" />
              </Field>
              <Field label="Document type">
                <select value={form.document_type} data-testid="onboarding-select-doc-type"
                  onChange={(e) => setForm({ ...form, document_type: e.target.value })}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white">
                  <option value="ID_CARD">National ID Card</option>
                  <option value="PASSPORT">Passport</option>
                  <option value="DRIVER_LICENSE">Driver License</option>
                </select>
              </Field>
              <Field label="Wallet address (optional)">
                <input type="text" placeholder="0x..." data-testid="onboarding-input-wallet"
                  value={form.wallet_address}
                  onChange={(e) => setForm({ ...form, wallet_address: e.target.value })}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white font-mono text-sm" />
              </Field>
            </div>
            <div className="flex justify-end mt-6">
              <button
                onClick={startKyc}
                disabled={submitting}
                data-testid="onboarding-continue-step-0"
                className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-2.5 rounded-lg font-medium flex items-center gap-2 disabled:opacity-50"
              >
                {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
                Continue
              </button>
            </div>
          </div>
        )}

        {/* Step 1 — ID Document */}
        {step === 1 && (
          <div className="bg-white/5 backdrop-blur rounded-2xl p-6 border border-white/10" data-testid="step-id-document">
            <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <FileText className="h-5 w-5 text-purple-400" /> Upload ID Document
            </h2>
            <p className="text-gray-400 text-sm mb-6">
              Upload a clear photo of your {form.document_type.replace('_', ' ').toLowerCase()}.
              Make sure all four corners are visible and the text is readable.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <UploadBox
                label="Front side"
                done={uploaded.ID_FRONT}
                onPick={() => idFrontRef.current?.click()}
                testId="upload-id-front"
              />
              <input ref={idFrontRef} type="file" accept="image/*,application/pdf" hidden
                onChange={(e) => upload('ID_FRONT', e.target.files?.[0])} />
              <UploadBox
                label="Back side"
                done={uploaded.ID_BACK}
                onPick={() => idBackRef.current?.click()}
                testId="upload-id-back"
                optional={form.document_type === 'PASSPORT'}
              />
              <input ref={idBackRef} type="file" accept="image/*,application/pdf" hidden
                onChange={(e) => upload('ID_BACK', e.target.files?.[0])} />
            </div>
            <div className="flex justify-between mt-6">
              <button onClick={() => setStep(0)} data-testid="onboarding-back-step-1"
                className="text-gray-300 hover:text-white px-4 py-2 flex items-center gap-2">
                <ArrowLeft className="h-4 w-4" /> Back
              </button>
              <button
                onClick={() => setStep(2)}
                disabled={!uploaded.ID_FRONT}
                data-testid="onboarding-continue-step-1"
                className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-2.5 rounded-lg font-medium flex items-center gap-2 disabled:opacity-50"
              >
                Continue <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}

        {/* Step 2 — Selfie */}
        {step === 2 && (
          <div className="bg-white/5 backdrop-blur rounded-2xl p-6 border border-white/10" data-testid="step-selfie">
            <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <Camera className="h-5 w-5 text-purple-400" /> Selfie verification
            </h2>
            <p className="text-gray-400 text-sm mb-6">
              Hold your ID next to your face. Take the photo in good lighting with no glasses or hats.
            </p>
            <UploadBox
              label="Take or upload a selfie"
              done={uploaded.SELFIE}
              onPick={() => selfieRef.current?.click()}
              testId="upload-selfie"
              big
            />
            <input ref={selfieRef} type="file" accept="image/*" capture="user" hidden
              onChange={(e) => upload('SELFIE', e.target.files?.[0])} />
            <div className="flex justify-between mt-6">
              <button onClick={() => setStep(1)} data-testid="onboarding-back-step-2"
                className="text-gray-300 hover:text-white px-4 py-2 flex items-center gap-2">
                <ArrowLeft className="h-4 w-4" /> Back
              </button>
              <button
                onClick={() => setStep(3)}
                disabled={!uploaded.SELFIE}
                data-testid="onboarding-submit-for-review"
                className="bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-2.5 rounded-lg font-medium flex items-center gap-2 disabled:opacity-50"
              >
                Submit for Review <CheckCircle2 className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}

        {/* Step 3 — Status */}
        {step === 3 && (
          <div className="bg-white/5 backdrop-blur rounded-2xl p-6 border border-white/10 text-center" data-testid="step-status">
            <StatusIcon className={`h-16 w-16 mx-auto mb-4 ${meta.color.split(' ')[1] || 'text-white'}`} />
            <h2 className="text-2xl font-semibold text-white mb-2">{meta.label}</h2>
            <p className="text-gray-400 max-w-md mx-auto">
              {status === 'APPROVED'
                ? 'You can now trade on NeoNoble Ramp. Welcome aboard!'
                : status === 'REJECTED'
                ? 'Please contact support@neonoble-ramp.com to discuss next steps.'
                : 'Our MLRO team will review your application within 1–2 business days. You will receive an email when the decision is made.'}
            </p>
            <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-md mx-auto text-left">
              {kyc?.full_name && <SummaryRow label="Name" value={kyc.full_name} />}
              {kyc?.nationality && <SummaryRow label="Nationality" value={kyc.nationality} />}
              {kyc?.document_type && <SummaryRow label="Document" value={kyc.document_type.replace('_', ' ')} />}
              {kyc?.submitted_at && <SummaryRow label="Submitted" value={new Date(kyc.submitted_at).toLocaleDateString()} />}
            </div>
            <button
              onClick={() => navigate('/dashboard')}
              data-testid="onboarding-go-to-dashboard"
              className="mt-8 bg-purple-600 hover:bg-purple-700 text-white px-6 py-2.5 rounded-lg font-medium"
            >
              Go to Dashboard
            </button>
          </div>
        )}

        <p className="mt-6 text-xs text-gray-500 text-center">
          Data is processed under GDPR &amp; MiCAR. Documents are encrypted at rest and reviewed
          by NeoNoble Technology Inc. Ltd. — registered CASP.
        </p>
      </main>
    </div>
  );
}

function Field({ label, required, children }) {
  return (
    <label className="block">
      <span className="text-sm text-gray-300 mb-1 block">
        {label} {required && <span className="text-red-400">*</span>}
      </span>
      {children}
    </label>
  );
}

function UploadBox({ label, done, onPick, testId, big = false, optional = false }) {
  return (
    <button
      type="button"
      onClick={onPick}
      data-testid={testId}
      className={`w-full border-2 border-dashed rounded-xl flex flex-col items-center justify-center gap-2 transition-colors ${
        done ? 'border-emerald-400 bg-emerald-500/10' : 'border-white/20 hover:border-purple-400 bg-white/5'
      } ${big ? 'py-12' : 'py-8'}`}
    >
      {done ? (
        <CheckCircle2 className="h-8 w-8 text-emerald-400" />
      ) : (
        <Upload className="h-8 w-8 text-gray-400" />
      )}
      <span className="text-sm font-medium text-white">{label}</span>
      {optional && <span className="text-xs text-gray-500">Optional for passport</span>}
      {done && <span className="text-xs text-emerald-400">Uploaded</span>}
    </button>
  );
}

function SummaryRow({ label, value }) {
  return (
    <div className="flex justify-between text-sm bg-white/5 rounded-lg px-3 py-2">
      <span className="text-gray-400">{label}</span>
      <span className="text-white">{value}</span>
    </div>
  );
}
