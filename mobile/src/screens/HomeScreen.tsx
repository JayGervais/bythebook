import { useCallback, useState } from 'react';
import { Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { api, MaintenanceTask, prettyDate, Reminder, Tenancy } from '../api';
import { RootParamList } from '../navigation';
import { Card, colors, ErrorText } from '../ui';
import { Tabs } from './Tabs';

type Home = { reminders: Reminder[]; tenancies: Tenancy[]; maintenance: MaintenanceTask[] };

export function HomeScreen({ navigation }: NativeStackScreenProps<RootParamList, 'Home'>) {
  const [home, setHome] = useState<Home | null>(null);
  const [error, setError] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      setHome(await api<Home>('/api/home/'));
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load your records.');
    }
  }, []);

  useFocusEffect(useCallback(() => { void load(); }, [load]));

  return (
    <View style={styles.screen}>
      <ScrollView
        contentContainerStyle={styles.page}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load().finally(() => setRefreshing(false)); }} />}
      >
        <Text style={styles.lede}>Open deadlines across your properties.</Text>
        {error ? <ErrorText>{error}</ErrorText> : null}
        {home?.reminders.length === 0 && <Card><Text style={styles.body}>No open deadlines.</Text></Card>}
        {!!home?.reminders.length && <Text style={styles.section}>Due soon</Text>}
        {home?.reminders.map((reminder) => (
          <Pressable accessibilityRole="button" key={reminder.id} onPress={() => navigation.navigate('Tenancy', { id: reminder.tenancy_id })}>
            <Card>
              <Text style={styles.due}>{reminder.unit} · due {prettyDate(reminder.due_on)}</Text>
              <Text style={styles.heading}>{reminder.headline}</Text>
              <Text style={styles.body}>{reminder.detail}</Text>
            </Card>
          </Pressable>
        ))}
        {!!home?.maintenance.length && <Text style={styles.section}>Maintenance</Text>}
        {home?.maintenance.map((task) => (
          <Pressable accessibilityRole="button" key={task.id} onPress={() => navigation.navigate('Properties')}>
            <Card>
              <Text style={styles.task}>{task.unit_label} · due {prettyDate(task.next_due_on)}</Text>
              <Text style={styles.heading}>{task.label}</Text>
            </Card>
          </Pressable>
        ))}
        {!!home?.tenancies.length && <Text style={styles.section}>Tenancies</Text>}
        {home?.tenancies.map((tenancy) => (
          <Pressable accessibilityRole="button" key={tenancy.id} onPress={() => navigation.navigate('Tenancy', { id: tenancy.id })}>
            <Card>
              <View style={styles.row}>
                <Text style={styles.heading}>{tenancy.unit_label}</Text>
                <Text style={styles.pill}>{tenancy.status}</Text>
              </View>
              <Text style={styles.muted}>{tenancy.address} · {tenancy.tenants.map((tenant) => tenant.name).join(', ')}</Text>
            </Card>
          </Pressable>
        ))}
      </ScrollView>
      <Tabs active="Home" />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.canvas },
  page: { padding: 20, gap: 12, paddingBottom: 28 },
  lede: { color: colors.muted, fontSize: 16, lineHeight: 22 },
  section: { marginTop: 10, color: colors.muted, fontSize: 12, fontWeight: '600', letterSpacing: 0.8, textTransform: 'uppercase' },
  muted: { color: colors.muted, fontSize: 13 },
  due: { color: colors.amber, fontSize: 13, fontWeight: '700' },
  task: { color: colors.tide, fontSize: 13, fontWeight: '700' },
  body: { color: colors.ink, lineHeight: 21 },
  heading: { fontSize: 17, fontWeight: '600', color: colors.ink, flexShrink: 1 },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 },
  pill: { backgroundColor: colors.accentSoft, color: colors.accentDeep, overflow: 'hidden', borderRadius: 999, paddingHorizontal: 10, paddingVertical: 4, fontSize: 12, fontWeight: '700', textTransform: 'capitalize' },
});
