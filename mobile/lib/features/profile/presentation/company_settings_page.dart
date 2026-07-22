import 'package:flutter/material.dart';
import 'package:mobile/core/di/injection.dart';
import 'package:mobile/core/network/api_exception.dart';
import 'package:mobile/core/theme/app_spacing.dart';
import 'package:mobile/shared/widgets/loading_view.dart';
import 'package:mobile/shared/widgets/responsive_scaffold.dart';

import '../data/company_settings_repository.dart';

const double _kMaxFormWidth = 560;

/// Form for the 7 `CompanySettings` fields, backed by
/// `GET`/`PATCH /companies/settings`. Read access requires
/// `Permission.companyView`; only [canManageCompanySettings] callers may
/// submit changes (gated server-side by `Permission.companyManageSettings`)
/// — when `false` the form renders read-only and the submit button is
/// hidden, matching what the backend would reject anyway.
class CompanySettingsPage extends StatefulWidget {
  const CompanySettingsPage({
    super.key,
    required this.canManageCompanySettings,
  });

  final bool canManageCompanySettings;

  @override
  State<CompanySettingsPage> createState() => _CompanySettingsPageState();
}

class _CompanySettingsPageState extends State<CompanySettingsPage> {
  late Future<CompanySettings> _loadFuture;

  CompanySettings? _original;
  bool _isSubmitting = false;

  final _nearDistanceController = TextEditingController();
  final _retentionDaysController = TextEditingController();
  final _offlineAfterController = TextEditingController();
  bool _trackingEnabled = false;
  int _trackingStartHour = 0;
  int _trackingEndHour = 23;

  @override
  void initState() {
    super.initState();
    _loadFuture = _load();
  }

  Future<CompanySettings> _load() async {
    final settings = await getIt<CompanySettingsRepository>().getSettings();
    _applySettings(settings);
    return settings;
  }

  void _applySettings(CompanySettings settings) {
    _original = settings;
    _nearDistanceController.text = settings.nearDistanceMeters.toString();
    _retentionDaysController.text = settings.locationRetentionDays.toString();
    _offlineAfterController.text = settings.offlineAfterMinutes.toString();
    _trackingEnabled = settings.trackingEnabled;
    _trackingStartHour = settings.trackingStartHour;
    _trackingEndHour = settings.trackingEndHour;
  }

  @override
  void dispose() {
    _nearDistanceController.dispose();
    _retentionDaysController.dispose();
    _offlineAfterController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final original = _original;
    if (original == null) return;

    final nearDistanceMeters = int.tryParse(_nearDistanceController.text);
    final locationRetentionDays = int.tryParse(
      _retentionDaysController.text,
    );
    final offlineAfterMinutes = int.tryParse(_offlineAfterController.text);
    if (nearDistanceMeters == null ||
        locationRetentionDays == null ||
        offlineAfterMinutes == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter valid numbers.')),
      );
      return;
    }

    setState(() => _isSubmitting = true);
    try {
      final updated = await getIt<CompanySettingsRepository>().updateSettings(
        nearDistanceMeters: nearDistanceMeters != original.nearDistanceMeters
            ? nearDistanceMeters
            : null,
        trackingEnabled: _trackingEnabled != original.trackingEnabled
            ? _trackingEnabled
            : null,
        trackingStartHour: _trackingStartHour != original.trackingStartHour
            ? _trackingStartHour
            : null,
        trackingEndHour: _trackingEndHour != original.trackingEndHour
            ? _trackingEndHour
            : null,
        locationRetentionDays:
            locationRetentionDays != original.locationRetentionDays
            ? locationRetentionDays
            : null,
        offlineAfterMinutes: offlineAfterMinutes != original.offlineAfterMinutes
            ? offlineAfterMinutes
            : null,
      );
      if (!mounted) return;
      setState(() => _applySettings(updated));
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Company settings updated.')),
      );
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Company settings')),
      body: SafeArea(
        child: FutureBuilder<CompanySettings>(
          future: _loadFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const LoadingView();
            }
            if (snapshot.hasError) {
              final message = snapshot.error is ApiException
                  ? (snapshot.error as ApiException).message
                  : 'Failed to load company settings.';
              return Center(child: Text(message));
            }
            return _buildForm(context);
          },
        ),
      ),
    );
  }

  Widget _buildForm(BuildContext context) {
    final readOnly = !widget.canManageCompanySettings;

    final form = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (readOnly)
          Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.md),
            child: Text(
              'You have view-only access to these settings.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
        TextField(
          controller: _nearDistanceController,
          enabled: !readOnly,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(
            labelText: 'Geofence "near" distance',
            suffixText: 'meters',
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        SwitchListTile(
          value: _trackingEnabled,
          onChanged: readOnly
              ? null
              : (value) => setState(() => _trackingEnabled = value),
          title: const Text('Location tracking enabled'),
          contentPadding: EdgeInsets.zero,
        ),
        const SizedBox(height: AppSpacing.sm),
        Row(
          children: [
            Expanded(
              child: _HourDropdown(
                label: 'Tracking start hour',
                value: _trackingStartHour,
                enabled: !readOnly,
                onChanged: (value) =>
                    setState(() => _trackingStartHour = value),
              ),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: _HourDropdown(
                label: 'Tracking end hour',
                value: _trackingEndHour,
                enabled: !readOnly,
                onChanged: (value) =>
                    setState(() => _trackingEndHour = value),
              ),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.md),
        TextField(
          controller: _retentionDaysController,
          enabled: !readOnly,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(
            labelText: 'Location retention',
            suffixText: 'days',
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        TextField(
          controller: _offlineAfterController,
          enabled: !readOnly,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(
            labelText: 'Offline after',
            suffixText: 'minutes',
          ),
        ),
        if (!readOnly) ...[
          const SizedBox(height: AppSpacing.lg),
          FilledButton(
            onPressed: _isSubmitting ? null : _submit,
            child: _isSubmitting
                ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Save changes'),
          ),
        ],
      ],
    );

    return ResponsiveScaffold(
      compact: (context) => SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: form,
      ),
      expanded: (context) => SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.xl),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: _kMaxFormWidth),
            child: form,
          ),
        ),
      ),
    );
  }
}

class _HourDropdown extends StatelessWidget {
  const _HourDropdown({
    required this.label,
    required this.value,
    required this.enabled,
    required this.onChanged,
  });

  final String label;
  final int value;
  final bool enabled;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    return DropdownButtonFormField<int>(
      initialValue: value,
      decoration: InputDecoration(labelText: label),
      items: [
        for (var hour = 0; hour < 24; hour++)
          DropdownMenuItem(value: hour, child: Text(hour.toString())),
      ],
      onChanged: enabled ? (v) => onChanged(v ?? value) : null,
    );
  }
}
