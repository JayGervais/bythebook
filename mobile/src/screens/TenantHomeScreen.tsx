import { useCallback, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { api, prettyDate } from '../api';
import { Button, Card, colors, ErrorText, Field } from '../ui';
import { Tabs } from './Tabs';

type Reminder = { id: string; due_on: string; headline: string; detail: string; unit: string };
type Message = { id: string; author_name: string; body: string };
type Home = { name: string; address: string; unit: string; reminders: Reminder[]; messages: Message[] };

export function TenantHomeScreen() {
  const [home, setHome] = useState<Home | null>(null);
  const [note, setNote] = useState('');
  const [error, setError] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      setHome(await api<Home>('/api/tenant/home/'));
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load your tenancy.');
    }
  }, []);

  useFocusEffect(useCallback(() => { void load(); }, [load]));

  async function send() {
    setError('');
    try {
      await api('/api/tenant/messages/', { method: 'POST', body: JSON.stringify({ body: note }) });
      setNote('');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not send that message.');
    }
  }

  return (
    <View style={styles.screen}>
      <ScrollView
        contentContainerStyle={styles.page}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load().finally(() => setRefreshing(false)); }} />}
      >
        <Text style={styles.lede}>{home ? `${home.unit} · ${home.address}` : 'Messages and reminders for your rental.'}</Text>
        {error ? <ErrorText>{error}</ErrorText> : null}
        {!!home?.reminders.length && <Text style={styles.section}>Reminders</Text>}
        {home?.reminders.map((reminder) => (
          <Card key={reminder.id}>
            <Text style={styles.due}>{reminder.unit} · due {prettyDate(reminder.due_on)}</Text>
            <Text style={styles.heading}>{reminder.headline}</Text>
            <Text style={styles.body}>{reminder.detail}</Text>
          </Card>
        ))}
        <Text style={styles.section}>Messages</Text>
        {home?.messages.length === 0 && <Card><Text style={styles.body}>No messages yet.</Text></Card>}
        {home?.messages.map((row) => (
          <Card key={row.id}>
            <Text style={styles.heading}>{row.author_name}</Text>
            <Text style={styles.body}>{row.body}</Text>
          </Card>
        ))}
        <Field label="Message" value={note} onChangeText={setNote} />
        <Button label="Send" onPress={() => void send()} />
      </ScrollView>
      <Tabs active="Home" />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.canvas },
  page: { padding: 20, gap: 12, paddingBottom: 28 },
  lede: { color: colors.muted, fontSize: 16, lineHeight: 22 },
  section: { marginTop: 10, color: colors.brandStrong, fontSize: 12, fontWeight: '600', letterSpacing: 1.2, textTransform: 'uppercase' },
  due: { color: colors.amber, fontSize: 13, fontWeight: '700' },
  body: { color: colors.ink, lineHeight: 21 },
  heading: { fontSize: 17, fontWeight: '600', color: colors.ink },
});
