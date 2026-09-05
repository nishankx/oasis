import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { Loader2, AlertCircle, Home } from 'lucide-react';
import { GithubIcon } from '../components/ui/GithubIcon';
import { api } from '../lib/api';
import { useAuthStore } from '../store/useAuthStore';
import { useTelemetryStore } from '../store/useTelemetryStore';

export const AuthCallbackPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { setSession, loginWithGithub } = useAuthStore();
  const { addToast } = useTelemetryStore();

  const [statusText, setStatusText] = useState<string>('Verifying authorization code with GitHub...');
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState<boolean>(true);

  useEffect(() => {
    const code = searchParams.get('code');

    if (!code) {
      setError('No OAuth authorization code detected in callback parameters.');
      setIsProcessing(false);
      return;
    }

    let isMounted = true;

    const processAuth = async () => {
      try {
        setStatusText('Exchanging authorization code for Oasis session...');
        const callbackUri = `${window.location.origin}/auth/callback`;
        const res = await api.callbackGitHub(code, callbackUri);

        if (!isMounted) return;

        if (res.authenticated && res.user && res.token) {
          setStatusText('Authorization verified. Launching discovery...');
          setSession(res.user, res.token);
          addToast({
            type: 'success',
            title: 'AUTHENTICATION VERIFIED',
            message: `Welcome @${res.user.username}. Session token issued.`,
          });
          navigate('/discovery', { replace: true });
        } else {
          throw new Error('Authentication succeeded but returned an incomplete session payload.');
        }
      } catch (err: any) {
        if (!isMounted) return;
        setError(err.message || 'GitHub OAuth verification failed. Please try signing in again.');
        setIsProcessing(false);
      }
    };

    processAuth();

    return () => {
      isMounted = false;
    };
  }, [searchParams, navigate, setSession, addToast]);

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 bg-[#000000]">
      <div className="w-full max-w-md rounded-[6px] bg-white/[0.02] p-8 shadow-2xl space-y-6 text-center">
        {/* Processing State */}
        {isProcessing && !error && (
          <div className="py-6 flex flex-col items-center justify-center space-y-4">
            <Loader2 className="h-8 w-8 text-accent-violet animate-spin" />
            <div className="space-y-1">
              <h2 className="font-display font-bold text-base text-white">
                Authenticating with GitHub
              </h2>
              <p className="text-xs text-text-secondary">{statusText}</p>
            </div>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="space-y-4 text-left">
            <div className="p-4 rounded-[4px] bg-accent-error/10 text-xs">
              <div className="flex items-center gap-2 text-accent-error font-semibold mb-1">
                <AlertCircle className="h-4 w-4" />
                <span>Authentication Failed</span>
              </div>
              <p className="text-text-secondary leading-relaxed">{error}</p>
            </div>

            <div className="flex flex-col sm:flex-row gap-2 pt-2">
              <button
                onClick={() => loginWithGithub()}
                className="flex-1 flex items-center justify-center gap-2 bg-accent-violet hover:bg-accent-violet-hover text-white font-medium text-xs py-2 px-4 rounded-[4px] transition-all cursor-pointer"
              >
                <GithubIcon className="h-3.5 w-3.5" />
                <span>Try Again</span>
              </button>

              <Link
                to="/"
                className="flex items-center justify-center gap-2 bg-white/[0.04] hover:bg-white/[0.08] text-white text-xs py-2 px-4 rounded-[4px] transition-colors"
              >
                <Home className="h-3.5 w-3.5" />
                <span>Home</span>
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
