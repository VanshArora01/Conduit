'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useAuth } from '@/contexts/auth-context';
import { useTheme } from '@/contexts/theme-context';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { StatusChip } from '@/components/ui/status-chip';
import { toast } from '@/components/ui/toast';
import {
  User,
  HardDrive,
  Sun,
  Moon,
  Monitor,
  Check,
  Shield,
  Layers,
} from 'lucide-react';
import type { Integration } from '@/types';

type SettingsTab = 'profile' | 'sources' | 'appearance' | 'account';

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { theme, setTheme } = useTheme();
  const [activeTab, setActiveTab] = useState<SettingsTab>('profile');

  // Profile forms
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [username, setUsername] = useState(user?.username || '');
  const [profileSaved, setProfileSaved] = useState(false);

  // Fetch connected integrations
  const { data: integrations = [], refetch: refetchIntegrations } = useQuery<Integration[]>({
    queryKey: ['integrations'],
    queryFn: () => api<Integration[]>('/integrations'),
  });

  const updateProfileMutation = useMutation({
    mutationFn: () =>
      api('/auth/me', {
        method: 'PATCH',
        body: { full_name: fullName, username },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user'] });
      setProfileSaved(true);
      setTimeout(() => setProfileSaved(false), 2000);
    },
    onError: (err: any) => {
      toast(err.message || 'Failed to update profile', 'error');
    },
  });

  // Integration connect logic
  const connectGoogleDrive = useMutation({
    mutationFn: async () => {
      const data = await api<{ url: string }>('/integrations/google/connect');
      const popup = window.open(data.url, 'google-oauth', 'width=500,height=600');
      
      const interval = setInterval(async () => {
        if (popup?.closed) {
          clearInterval(interval);
          refetchIntegrations();
          toast('Google Drive connected successfully.', 'success');
        }
      }, 1000);
    },
  });

  return (
    <div className="flex-1 flex overflow-hidden">
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto px-8 py-8">
        <h1 className="text-display-sm mb-6" style={{ color: 'var(--text-primary)' }}>
          Settings
        </h1>

        <div className="flex gap-8 flex-col md:flex-row items-start">
          {/* Tab Sub-nav */}
          <nav className="flex flex-col gap-1 w-full md:w-48 flex-shrink-0">
            <TabButton
              active={activeTab === 'profile'}
              onClick={() => setActiveTab('profile')}
              icon={<User size={16} />}
              label="Profile"
            />
            <TabButton
              active={activeTab === 'sources'}
              onClick={() => setActiveTab('sources')}
              icon={<HardDrive size={16} />}
              label="Connected Sources"
            />
            <TabButton
              active={activeTab === 'appearance'}
              onClick={() => setActiveTab('appearance')}
              icon={<Sun size={16} />}
              label="Appearance"
            />
          </nav>

          {/* Form area */}
          <div
            className="flex-1 max-w-xl w-full p-6 rounded-2xl border"
            style={{
              backgroundColor: 'var(--surface)',
              borderColor: 'var(--border)',
            }}
          >
            {/* Tab 1: Profile */}
            {activeTab === 'profile' && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-heading" style={{ color: 'var(--text-primary)' }}>
                    Profile Settings
                  </h3>
                  <p className="text-body mt-1" style={{ color: 'var(--text-secondary)' }}>
                    Update your personal profile details.
                  </p>
                </div>

                <div className="space-y-4">
                  <Input
                    label="Full Name"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                  />
                  <Input
                    label="Username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                  />
                  <Input
                    label="Email"
                    value={user?.email || ''}
                    disabled
                    hint="Your primary email address cannot be changed."
                  />
                </div>

                <div className="flex items-center gap-3 pt-2">
                  <Button
                    variant="primary"
                    onClick={() => updateProfileMutation.mutate()}
                    loading={updateProfileMutation.isPending}
                  >
                    Save Changes
                  </Button>
                  {profileSaved && (
                    <span className="text-caption flex items-center gap-1 text-emerald-500">
                      <Check size={14} /> Saved
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Tab 2: Sources */}
            {activeTab === 'sources' && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-heading" style={{ color: 'var(--text-primary)' }}>
                    Connected Sources
                  </h3>
                  <p className="text-body mt-1" style={{ color: 'var(--text-secondary)' }}>
                    Manage third-party knowledge connections.
                  </p>
                </div>

                <div className="divide-y divide-[var(--border)]">
                  {/* Google Drive source */}
                  <div className="flex items-center justify-between py-4">
                    <div className="flex items-center gap-3">
                      <HardDrive size={20} className="text-blue-500" />
                      <div>
                        <p className="text-body-medium font-semibold" style={{ color: 'var(--text-primary)' }}>
                          Google Drive
                        </p>
                        <p className="text-caption" style={{ color: 'var(--text-tertiary)' }}>
                          Google Drive document sync
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      {integrations.some((i) => i.provider === 'google_drive' && i.status === 'CONNECTED') ? (
                        <>
                          <StatusChip status="CONNECTED" />
                          <Button variant="secondary" size="compact" disabled>
                            Disconnect
                          </Button>
                        </>
                      ) : (
                        <Button
                          variant="primary"
                          size="compact"
                          onClick={() => connectGoogleDrive.mutate()}
                          loading={connectGoogleDrive.isPending}
                        >
                          Connect
                        </Button>
                      )}
                    </div>
                  </div>

                  {/* Future sources */}
                  <SourceRowDisabled name="GitHub" description="Import code repositories" />
                  <SourceRowDisabled name="Notion" description="Import wiki pages" />
                  <SourceRowDisabled name="Gmail" description="Import email logs" />
                </div>
              </div>
            )}

            {/* Tab 3: Appearance */}
            {activeTab === 'appearance' && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-heading" style={{ color: 'var(--text-primary)' }}>
                    Appearance Settings
                  </h3>
                  <p className="text-body mt-1" style={{ color: 'var(--text-secondary)' }}>
                    Select how Conduit displays in your browser.
                  </p>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <ThemeSelectCard
                    active={theme === 'light'}
                    onClick={() => setTheme('light')}
                    icon={<Sun size={18} />}
                    label="Light"
                  />
                  <ThemeSelectCard
                    active={theme === 'dark'}
                    onClick={() => setTheme('dark')}
                    icon={<Moon size={18} />}
                    label="Dark"
                  />
                  <ThemeSelectCard
                    active={theme === 'system'}
                    onClick={() => setTheme('system')}
                    icon={<Monitor size={18} />}
                    label="System"
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2.5 px-4 py-2.5 rounded-lg text-left text-body transition-colors cursor-pointer"
      style={{
        backgroundColor: active ? 'var(--accent-subtle)' : 'transparent',
        color: active ? 'var(--accent)' : 'var(--text-secondary)',
      }}
      onMouseEnter={(e) => {
        if (!active) e.currentTarget.style.backgroundColor = 'var(--bg-subtle)';
      }}
      onMouseLeave={(e) => {
        if (!active) e.currentTarget.style.backgroundColor = 'transparent';
      }}
    >
      <span style={{ color: active ? 'var(--accent)' : 'var(--text-tertiary)' }}>{icon}</span>
      <span className="font-medium">{label}</span>
    </button>
  );
}

function SourceRowDisabled({ name, description }: { name: string; description: string }) {
  return (
    <div className="flex items-center justify-between py-4 opacity-50 select-none">
      <div className="flex items-center gap-3">
        <Layers size={20} className="text-gray-400" />
        <div>
          <p className="text-body-medium font-semibold" style={{ color: 'var(--text-primary)' }}>{name}</p>
          <p className="text-caption" style={{ color: 'var(--text-tertiary)' }}>{description}</p>
        </div>
      </div>
      <span className="text-micro px-2 py-0.5 rounded-full" style={{ backgroundColor: 'var(--bg-subtle)', color: 'var(--text-tertiary)' }}>
        Coming soon
      </span>
    </div>
  );
}

function ThemeSelectCard({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className="flex flex-col items-center justify-center p-4 rounded-xl border transition-all cursor-pointer text-center"
      style={{
        borderColor: active ? 'var(--accent)' : 'var(--border)',
        backgroundColor: active ? 'var(--accent-subtle)' : 'var(--surface)',
      }}
    >
      <span className="mb-2" style={{ color: active ? 'var(--accent)' : 'var(--text-secondary)' }}>
        {icon}
      </span>
      <span className="text-caption font-semibold" style={{ color: active ? 'var(--accent)' : 'var(--text-primary)' }}>
        {label}
      </span>
    </button>
  );
}
