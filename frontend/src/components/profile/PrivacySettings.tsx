import React, { useState, useEffect } from 'react';
import { useHealthProfile } from '../../hooks/useHealthData';
import { userAPI } from '../../services/api';

export const PrivacySettings: React.FC = () => {
  const { profile, updateProfile } = useHealthProfile();
  const [settings, setSettings] = useState<any>({});
  const [saved, setSaved] = useState(false);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    if (profile?.privacy_settings) {
      setSettings(profile.privacy_settings);
    }
  }, [profile]);

  const handleSave = async () => {
    try {
      await updateProfile({ privacy_settings: settings });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (error) {
      console.error('Failed to save privacy settings:', error);
    }
  };

  const handleExportData = async () => {
    setExporting(true);
    try {
      const data = await userAPI.exportData();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `wellness-data-export-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (error) {
      console.error('Failed to export data:', error);
      alert('Failed to export data. Please try again.');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto mt-8 bg-white p-8 rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-6 text-gray-900">Privacy Settings</h2>

      <div className="space-y-4">
        <div>
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={settings.data_sharing || false}
              onChange={(e) => setSettings({ ...settings, data_sharing: e.target.checked })}
              className="mr-2"
            />
            <span className="text-gray-700">Allow data to be used for insights</span>
          </label>
        </div>

        <div>
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={settings.public_profile || false}
              onChange={(e) => setSettings({ ...settings, public_profile: e.target.checked })}
              className="mr-2"
            />
            <span className="text-gray-700">Make profile visible publicly</span>
          </label>
        </div>

        <div>
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={settings.email_notifications ?? true}
              onChange={(e) => setSettings({ ...settings, email_notifications: e.target.checked })}
              className="mr-2"
            />
            <span className="text-gray-700">Receive email notifications</span>
          </label>
        </div>
      </div>

      <div className="mt-6 space-y-4">
        <div>
          <h3 className="text-lg font-semibold mb-2 text-gray-900">Data Export (GDPR)</h3>
          <p className="text-sm text-gray-600 mb-2">
            Download all your personal data including health profile, metrics history, and AI insights.
          </p>
          <button
            onClick={handleExportData}
            disabled={exporting}
            className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50"
          >
            {exporting ? 'Exporting...' : 'Export My Data'}
          </button>
        </div>

        <div>
          <button
            onClick={handleSave}
            className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
          >
            Save Settings
          </button>
          {saved && <span className="ml-4 text-green-600">Settings saved!</span>}
        </div>
      </div>
    </div>
  );
};
