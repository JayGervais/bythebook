import { useCallback, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { api, money, prettyDate, Tenancy } from '../api';
import { RootParamList } from '../navigation';
import { Button, Card, colors, ErrorText, Field } from '../ui';

export function TenancyScreen({ route, navigation }: NativeStackScreenProps<RootParamList, 'Tenancy'>) {
  const { id } = route.params;
  const [tenancy, setTenancy] = useState<Tenancy | null>(null);
  const [error, setError] = useState('');
  const [paidOn, setPaidOn] = useState('');
  const [note, setNote] = useState('');
  const [message, setMessage] = useState('');
  const [request, setRequest] = useState('');

  const load = useCallback(async () => {
    if (!id) return;
    try {
      setTenancy(await api<Tenancy>(`/api/tenancies/${id}/`));
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load the tenancy.');
    }
  }, [id]);

  useFocusEffect(useCallback(() => { void load(); }, [load]));

  async function addPayment() {
    if (!tenancy) return;
    setError('');
    try {
      await api(`/api/tenancies/${tenancy.id}/payments/`, {
        method: 'POST',
        body: JSON.stringify({ amount: tenancy.rent_amount, paid_on: paidOn, method: 'etransfer', note }),
      });
      setPaidOn('');
      setNote('');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not record that payment.');
    }
  }

  async function addMessage() {
    if (!tenancy) return;
    setError('');
    try {
      await api(`/api/tenancies/${tenancy.id}/messages/`, { method: 'POST', body: JSON.stringify({ body: message }) });
      setMessage('');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save that message.');
    }
  }

  async function addRequest() {
    if (!tenancy) return;
    setError('');
    try {
      await api(`/api/units/${tenancy.unit}/requests/`, {
        method: 'POST',
        body: JSON.stringify({ description: request, tenancy: tenancy.id }),
      });
      setRequest('');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save that request.');
    }
  }

  async function setStatus(requestId: string, status: string) {
    setError('');
    try {
      await api(`/api/maintenance-requests/${requestId}/`, { method: 'PATCH', body: JSON.stringify({ status }) });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update that request.');
    }
  }

  if (!id) {
    return <View style={styles.page}><Text>Open a tenancy from Home.</Text></View>;
  }

  return (
    <ScrollView contentContainerStyle={styles.page} keyboardShouldPersistTaps="handled">
      {error ? <ErrorText>{error}</ErrorText> : null}
      {tenancy && (
        <>
          <Text style={styles.muted}>{tenancy.address}</Text>
          <Text style={styles.title}>{tenancy.unit_label}</Text>
          <Text style={styles.summary}>{tenancy.tenants.map((tenant) => tenant.name).join(', ')} · <Text style={styles.rent}>{money(tenancy.rent_amount)}</Text> · due on day {tenancy.rent_due_day}</Text>
          {tenancy.deposit && <Text style={styles.deposit}>Deposit balance {money(tenancy.deposit.balance)}</Text>}

          <Card>
            <Text style={styles.heading}>Inspections</Text>
            {tenancy.inspections.map((inspection) => (
              <Pressable accessibilityRole="button" key={inspection.id} onPress={() => navigation.navigate('Inspection', { id: inspection.id })}>
                <Text style={styles.link}>
                  {inspection.inspection_type === 'move_in' ? 'Move-in' : 'Move-out'} · version {inspection.version}
                  {inspection.is_locked ? ` · finished ${prettyDate(inspection.finalized_at)}` : ' · draft'}
                </Text>
              </Pressable>
            ))}
          </Card>

          <Card>
            <Text style={styles.heading}>Rent received</Text>
            {tenancy.payments.map((payment) => (
              <Text key={payment.id}>{payment.receipt_number} · {prettyDate(payment.paid_on)} · {money(payment.amount)} · {payment.method_label}</Text>
            ))}
            <Field label="Date received (YYYY-MM-DD)" value={paidOn} onChangeText={setPaidOn} placeholder="2026-11-05" />
            <Field label="Note" value={note} onChangeText={setNote} />
            <Button label="Record e-Transfer" secondary onPress={() => void addPayment()} />
          </Card>

          <Card>
            <Text style={styles.heading}>Notices</Text>
            {tenancy.notices.map((notice) => (
              <Text key={notice.id}>{notice.kind.replace(/_/g, ' ')} · served {prettyDate(notice.served_on)} · effective {prettyDate(notice.effective_on)}</Text>
            ))}
            <Text style={styles.muted}>Create and check notice dates on the website. The phone keeps the copy you already saved.</Text>
          </Card>

          <Card>
            <Text style={styles.heading}>Messages</Text>
            {tenancy.messages.map((row) => <Text key={row.id}><Text style={styles.strong}>{row.author_name}: </Text>{row.body}</Text>)}
            <Field label="Note" value={message} onChangeText={setMessage} />
            <Button label="Save message" secondary onPress={() => void addMessage()} />
          </Card>

          <Card>
            <Text style={styles.heading}>Maintenance</Text>
            {tenancy.maintenance_requests.map((row) => (
              <View key={row.id} style={styles.block}>
                <Text>{row.description}</Text>
                <Text style={styles.muted}>{row.status.replace(/_/g, ' ')} · {row.requester_name}</Text>
                {row.status !== 'resolved' && <Button label="Resolved" secondary onPress={() => void setStatus(row.id, 'resolved')} />}
              </View>
            ))}
            <Field label="Request" value={request} onChangeText={setRequest} />
            <Button label="Add request" secondary onPress={() => void addRequest()} />
          </Card>
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { padding: 20, gap: 14, backgroundColor: colors.canvas },
  title: { fontSize: 28, fontWeight: '700', color: colors.ink, letterSpacing: -0.4 },
  summary: { color: colors.ink, lineHeight: 22 },
  rent: { color: colors.accentDeep, fontWeight: '700' },
  deposit: { alignSelf: 'flex-start', backgroundColor: colors.accentSoft, color: colors.accentDeep, overflow: 'hidden', borderRadius: 999, paddingHorizontal: 10, paddingVertical: 4, fontWeight: '700' },
  heading: { fontSize: 17, fontWeight: '700', color: colors.ink },
  muted: { color: colors.muted, lineHeight: 20 },
  link: { fontSize: 16, color: colors.accentDeep, fontWeight: '700' },
  strong: { fontWeight: '700', color: colors.ink },
  block: { gap: 6 },
});
