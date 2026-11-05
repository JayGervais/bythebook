import { StyleSheet, Text, View } from 'react-native';
import { useAuth } from '../auth';
import { Button, Card, colors } from '../ui';
import { Tabs } from './Tabs';

export function AccountScreen() {
  const { user, signOut } = useAuth();
  return (
    <View style={styles.screen}>
      <View style={styles.page}>
        <Card>
          <View style={styles.identity}>
            <View style={styles.avatar}><Text style={styles.avatarText}>{(user?.full_name || user?.email || 'A').slice(0, 1).toUpperCase()}</Text></View>
            <View style={styles.identityText}>
              <Text style={styles.heading}>{user?.full_name || 'Account'}</Text>
              <Text style={styles.muted}>{user?.email}</Text>
            </View>
          </View>
          {user?.phone ? <Text>{user.phone}</Text> : null}
          {user?.address_for_service ? <Text>{user.address_for_service}</Text> : null}
        </Card>
        <Text style={styles.muted}>Not legal advice. Check the current Residential Tenancies Act before you rely on a notice or a deadline.</Text>
        <Button label="Sign out" secondary onPress={() => void signOut()} />
      </View>
      <Tabs active="Account" />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.canvas },
  page: { flex: 1, padding: 20, gap: 16 },
  identity: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  identityText: { flex: 1, gap: 2 },
  avatar: { width: 48, height: 48, borderRadius: 24, backgroundColor: colors.brandSoft, borderWidth: 1, borderColor: colors.brand, alignItems: 'center', justifyContent: 'center' },
  avatarText: { color: colors.brandStrong, fontSize: 20, fontWeight: '600' },
  heading: { fontSize: 20, fontWeight: '700', color: colors.ink },
  muted: { color: colors.muted, lineHeight: 20 },
});
