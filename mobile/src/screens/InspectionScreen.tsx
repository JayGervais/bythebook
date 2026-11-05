import { useCallback, useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { api, Inspection, InspectionItem } from '../api';
import { RootParamList } from '../navigation';
import { Button, Card, colors, ErrorText } from '../ui';

const CONDITIONS = [
  ['good', 'Good'],
  ['fair', 'Fair'],
  ['poor', 'Poor'],
  ['damaged', 'Damaged'],
  ['not_applicable', 'N/A'],
] as const;

export function InspectionScreen({ route }: NativeStackScreenProps<RootParamList, 'Inspection'>) {
  const { id } = route.params;
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState('');

  const load = useCallback(async () => {
    try {
      setInspection(await api<Inspection>(`/api/inspections/${id}/`));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load the inspection.');
    }
  }, [id]);

  useEffect(() => { void load(); }, [load]);

  function setCondition(itemId: string, condition: string) {
    setInspection((current) => current && ({
      ...current,
      items: current.items.map((item) => item.id === itemId ? { ...item, condition } : item),
    }));
  }

  async function save() {
    if (!inspection) return;
    setError('');
    setSaved('');
    try {
      setInspection(await api<Inspection>(`/api/inspections/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify({
          items: inspection.items.map((item) => ({ id: item.id, condition: item.condition, notes: item.notes })),
        }),
      }));
      setSaved('Draft saved.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save the draft.');
    }
  }

  const rooms: { room: string; items: InspectionItem[] }[] = [];
  for (const item of inspection?.items || []) {
    const group = rooms.find((entry) => entry.room === item.room);
    if (group) group.items.push(item);
    else rooms.push({ room: item.room, items: [item] });
  }

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <Text style={styles.title}>{inspection?.inspection_type === 'move_out' ? 'Move-out inspection' : 'Move-in inspection'}</Text>
      {error ? <ErrorText>{error}</ErrorText> : null}
      {saved ? <Text style={styles.saved}>{saved}</Text> : null}
      {inspection?.blockers.map((blocker) => <Text key={blocker} style={styles.muted}>{blocker}</Text>)}
      {rooms.map((group) => (
        <Card key={group.room}>
          <Text style={styles.heading}>{group.room}</Text>
          {group.items.map((item) => (
            <View key={item.id} style={styles.item}>
              <Text style={styles.itemName}>{item.item}</Text>
              {item.prior_condition ? <Text style={styles.muted}>Move-in was {item.prior_condition}</Text> : null}
              <View style={styles.chips}>
                {CONDITIONS.map(([value, label]) => (
                  <Pressable accessibilityRole="button" key={value} onPress={() => setCondition(item.id, value)} disabled={inspection?.is_locked} style={[styles.chip, item.condition === value && styles.chipOn]}>
                    <Text style={[styles.chipText, item.condition === value && styles.chipTextOn]}>{label}</Text>
                  </Pressable>
                ))}
              </View>
            </View>
          ))}
        </Card>
      ))}
      {inspection && !inspection.is_locked && <Button label="Save draft" onPress={() => void save()} />}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { padding: 20, gap: 14, backgroundColor: colors.canvas },
  title: { fontSize: 26, fontWeight: '700', color: colors.ink },
  heading: { fontSize: 18, fontWeight: '600', color: colors.ink },
  muted: { color: colors.muted, lineHeight: 20 },
  saved: { color: colors.accentDeep, fontWeight: '700' },
  item: { gap: 8, paddingTop: 8, borderTopWidth: 1, borderTopColor: colors.line },
  itemName: { fontSize: 16, color: colors.ink, fontWeight: '600' },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  chip: { borderWidth: 1, borderColor: colors.line, backgroundColor: colors.canvas, borderRadius: 999, paddingHorizontal: 12, paddingVertical: 8 },
  chipOn: { backgroundColor: colors.brandSoft, borderColor: 'transparent' },
  chipText: { color: colors.ink, fontSize: 13, fontWeight: '600' },
  chipTextOn: { color: colors.brandStrong },
});
