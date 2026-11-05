import { useCallback, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { api, prettyDate, Property } from '../api';
import { RootParamList } from '../navigation';
import { Button, Card, colors, ErrorText, Field } from '../ui';
import { Tabs } from './Tabs';

export function PropertiesScreen({ navigation }: NativeStackScreenProps<RootParamList, 'Properties'>) {
  const [properties, setProperties] = useState<Property[]>([]);
  const [error, setError] = useState('');
  const [address, setAddress] = useState('');
  const [city, setCity] = useState('');
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [tenancyForm, setTenancyForm] = useState({ unit: '', name: '', rent: '', start: '' });

  const load = useCallback(async () => {
    try {
      const rows = await api<Property[]>('/api/properties/');
      setProperties(rows);
      setTenancyForm((current) => current.unit ? current : { ...current, unit: rows[0]?.units[0]?.id || '' });
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load properties.');
    }
  }, []);

  useFocusEffect(useCallback(() => { void load(); }, [load]));

  async function addProperty() {
    setError('');
    try {
      await api('/api/properties/', {
        method: 'POST',
        body: JSON.stringify({ street_address: address, city, province: 'AB', property_type: 'house_with_suite' }),
      });
      setAddress('');
      setCity('');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save the property.');
    }
  }

  async function addUnit(propertyId: string) {
    setError('');
    try {
      await api('/api/units/', {
        method: 'POST',
        body: JSON.stringify({ property: propertyId, label: labels[propertyId] || 'Unit 1' }),
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not add the unit.');
    }
  }

  async function startTenancy() {
    setError('');
    try {
      const created = await api<{ id: string }>('/api/tenancies/', {
        method: 'POST',
        body: JSON.stringify({
          unit_id: tenancyForm.unit,
          start_date: tenancyForm.start,
          rent_amount: tenancyForm.rent,
          rent_due_day: 1,
          period: 'monthly',
          tenants: [{ name: tenancyForm.name, email: '', phone: '' }],
        }),
      });
      navigation.navigate('Tenancy', { id: created.id });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save the tenancy.');
    }
  }

  async function markDone(taskId: string) {
    setError('');
    try {
      await api(`/api/maintenance-tasks/${taskId}/done/`, { method: 'POST', body: JSON.stringify({}) });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not update that task.');
    }
  }

  return (
    <View style={styles.screen}>
      <ScrollView contentContainerStyle={styles.page} keyboardShouldPersistTaps="handled">
        {error ? <ErrorText>{error}</ErrorText> : null}
        {properties.map((property) => (
          <Card key={property.id}>
            <Text style={styles.heading}>{property.street_address}</Text>
            <Text style={styles.muted}>{property.city}, Alberta</Text>
            {property.units.map((unit) => (
              <View key={unit.id} style={styles.block}>
                <Text style={styles.unit}>{unit.label}</Text>
                {(unit.tasks || []).map((task) => (
                  <View key={task.id} style={styles.row}>
                    <Text style={styles.task}>{task.label} · {prettyDate(task.next_due_on)}</Text>
                    <Pressable accessibilityRole="button" onPress={() => void markDone(task.id)}><Text style={styles.link}>Done</Text></Pressable>
                  </View>
                ))}
              </View>
            ))}
            <Field label="Unit name" value={labels[property.id] ?? 'Unit 1'} onChangeText={(value) => setLabels((current) => ({ ...current, [property.id]: value }))} />
            <Button label="Add unit" secondary onPress={() => void addUnit(property.id)} />
          </Card>
        ))}
        <Card>
          <Text style={styles.heading}>New tenancy</Text>
          <View style={styles.chips}>
            {properties.flatMap((property) => property.units.map((unit) => (
              <Pressable accessibilityRole="button" key={unit.id} onPress={() => setTenancyForm({ ...tenancyForm, unit: unit.id })} style={[styles.chip, tenancyForm.unit === unit.id && styles.chipOn]}>
                <Text style={tenancyForm.unit === unit.id ? styles.chipOnText : undefined}>{unit.label}</Text>
              </Pressable>
            )))}
          </View>
          <Field label="Tenant name" value={tenancyForm.name} onChangeText={(value) => setTenancyForm({ ...tenancyForm, name: value })} />
          <Field label="Monthly rent" value={tenancyForm.rent} onChangeText={(value) => setTenancyForm({ ...tenancyForm, rent: value })} keyboard="decimal-pad" />
          <Field label="Move-in (YYYY-MM-DD)" value={tenancyForm.start} onChangeText={(value) => setTenancyForm({ ...tenancyForm, start: value })} placeholder="2026-11-05" />
          <Button label="Save tenancy" onPress={() => void startTenancy()} />
        </Card>
        <Card>
          <Text style={styles.heading}>New property</Text>
          <Field label="Street address" value={address} onChangeText={setAddress} />
          <Field label="City" value={city} onChangeText={setCity} />
          <Button label="Save property" onPress={() => void addProperty()} />
        </Card>
      </ScrollView>
      <Tabs active="Properties" />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.canvas },
  page: { padding: 20, gap: 12 },
  heading: { fontSize: 18, fontWeight: '700', color: colors.ink },
  muted: { color: colors.muted },
  block: { gap: 6, marginTop: 8 },
  unit: { fontSize: 16, fontWeight: '700', color: colors.accentDeep },
  row: { flexDirection: 'row', justifyContent: 'space-between', gap: 12, alignItems: 'center' },
  task: { flex: 1, color: colors.ink },
  link: { fontWeight: '700', color: colors.accent },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: { borderWidth: 1, borderColor: colors.line, backgroundColor: colors.canvas, borderRadius: 999, paddingHorizontal: 12, paddingVertical: 8 },
  chipOn: { backgroundColor: colors.accent, borderColor: colors.accent },
  chipOnText: { color: '#fff', fontWeight: '700' },
});
