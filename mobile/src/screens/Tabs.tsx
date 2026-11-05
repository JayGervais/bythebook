import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootParamList } from '../navigation';
import { colors } from '../ui';

const items: { key: 'Home' | 'Properties' | 'Account'; label: string }[] = [
  { key: 'Home', label: 'Home' },
  { key: 'Properties', label: 'Properties' },
  { key: 'Account', label: 'Account' },
];

export function Tabs({ active }: { active: 'Home' | 'Properties' | 'Account' }) {
  const navigation = useNavigation<NativeStackNavigationProp<RootParamList>>();
  return (
    <View style={styles.bar}>
      <View style={styles.inner}>
        {items.map((item) => (
          <Pressable accessibilityRole="button" key={item.key} onPress={() => navigation.navigate(item.key)} style={[styles.item, active === item.key && styles.itemOn]}>
            <Text style={[styles.label, active === item.key && styles.on]}>{item.label}</Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  bar: { backgroundColor: colors.canvas, paddingHorizontal: 16, paddingTop: 6, paddingBottom: 12 },
  inner: { flexDirection: 'row', backgroundColor: '#eef0f3', borderRadius: 14, padding: 4 },
  item: { flex: 1, minHeight: 40, alignItems: 'center', justifyContent: 'center', borderRadius: 10 },
  itemOn: { backgroundColor: colors.card, shadowColor: '#12141a', shadowOpacity: 0.06, shadowRadius: 6, shadowOffset: { width: 0, height: 2 }, elevation: 1 },
  label: { color: colors.muted, fontSize: 13, fontWeight: '600' },
  on: { color: colors.ink },
});
