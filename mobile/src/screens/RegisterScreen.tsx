import { useState } from 'react';
import { ScrollView, StyleSheet } from 'react-native';
import { useAuth } from '../auth';
import { Button, colors, ErrorText, Field } from '../ui';

export function RegisterScreen() {
  const { register } = useAuth();
  const [form, setForm] = useState({ email: '', password: '', full_name: '', phone: '', address_for_service: '' });
  const [error, setError] = useState('');

  function set(key: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function submit() {
    setError('');
    try {
      await register(form);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create the account.');
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.page} keyboardShouldPersistTaps="handled">
      {error ? <ErrorText>{error}</ErrorText> : null}
      <Field label="Name" value={form.full_name} onChangeText={(value) => set('full_name', value)} />
      <Field label="Email" value={form.email} onChangeText={(value) => set('email', value)} keyboard="email-address" />
      <Field label="Password" value={form.password} onChangeText={(value) => set('password', value)} secure />
      <Field label="Phone" value={form.phone} onChangeText={(value) => set('phone', value)} />
      <Field label="Address for service" value={form.address_for_service} onChangeText={(value) => set('address_for_service', value)} />
      <Button label="Create account" onPress={() => void submit()} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { padding: 20, gap: 14, backgroundColor: colors.canvas },
});
