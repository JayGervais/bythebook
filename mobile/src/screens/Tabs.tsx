import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootParamList } from '../navigation';
import { useAuth } from '../auth';
import { colors } from '../ui';

const items: { key: 'Home' | 'Properties' | 'Account'; label: string }[] = [
  { key: 'Home', label: 'Home' },
  { key: 'Properties', label: 'Properties' },
  { key: 'Account', label: 'Account' },
];

export function Tabs({ active }: { active: 'Home' | 'Properties' | 'Account' }) {
  const navigation = useNavigation<NativeStackNavigationProp<RootParamList>>();
  const { user } = useAuth();
  const shown = user?.role === 'tenant' ? items.filter((item) => item.key !== 'Properties') : items;
  return (
    <View style={styles.bar}>
      <View style={styles.inner}>
        {shown.map((item) => (
          <Pressable accessibilityRole="button" key={item.key} onPress={() => navigation.navigate(item.key)} style={[styles.item, active === item.key && styles.itemOn]}>
            <Text style={[styles.label, active === item.key && styles.on]}>{item.label}</Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  bar: { backgroundColor: 'transparent', paddingHorizontal: 16, paddingTop: 6, paddingBottom: 14 },
  inner: {
    flexDirection: 'row',
    backgroundColor: 'rgba(255,255,255,0.92)',
    borderRadius: 20,
    padding: 4,
    borderWidth: 1,
    borderColor: 'rgba(122, 110, 98, 0.28)',
  },
  item: { flex: 1, minHeight: 40, alignItems: 'center', justifyContent: 'center', borderRadius: 16 },
  itemOn: { backgroundColor: colors.brandSoft },
  label: { color: colors.ink, fontSize: 13, fontWeight: '500' },
  on: { color: colors.brandStrong, fontWeight: '600' },
});
