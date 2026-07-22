import 'package:mobile/core/network/api_client.dart';

/// Mirrors `backend/app/schemas/company.py::CompanySettingsPublic`.
class CompanySettings {
  const CompanySettings({
    required this.nearDistanceMeters,
    required this.trackingEnabled,
    required this.trackingStartHour,
    required this.trackingEndHour,
    required this.locationRetentionDays,
    required this.offlineAfterMinutes,
  });

  /// Geofence "near" threshold, in meters.
  final int nearDistanceMeters;
  final bool trackingEnabled;

  /// Hour of day (0-23) tracking starts.
  final int trackingStartHour;

  /// Hour of day (0-23) tracking ends.
  final int trackingEndHour;
  final int locationRetentionDays;
  final int offlineAfterMinutes;

  factory CompanySettings.fromJson(Map<String, dynamic> json) {
    return CompanySettings(
      nearDistanceMeters: json['near_distance_meters'] as int,
      trackingEnabled: json['tracking_enabled'] as bool,
      trackingStartHour: json['tracking_start_hour'] as int,
      trackingEndHour: json['tracking_end_hour'] as int,
      locationRetentionDays: json['location_retention_days'] as int,
      offlineAfterMinutes: json['offline_after_minutes'] as int,
    );
  }
}

/// Repository for the `/companies/settings` endpoints. Reads are gated by
/// `Permission.companyView` and writes by `Permission.companyManageSettings`
/// on the backend (see `app/api/v1/companies.py`) — callers should check the
/// corresponding `Permission` before showing UI that hits this repository.
class CompanySettingsRepository {
  CompanySettingsRepository(this._apiClient);

  final ApiClient _apiClient;

  Future<CompanySettings> getSettings() async {
    final envelope = await _apiClient.get<CompanySettings>(
      '/companies/settings',
      fromData: (json) =>
          CompanySettings.fromJson(json as Map<String, dynamic>),
    );
    return envelope.data!;
  }

  Future<CompanySettings> updateSettings({
    int? nearDistanceMeters,
    bool? trackingEnabled,
    int? trackingStartHour,
    int? trackingEndHour,
    int? locationRetentionDays,
    int? offlineAfterMinutes,
  }) async {
    final envelope = await _apiClient.patch<CompanySettings>(
      '/companies/settings',
      body: {
        if (nearDistanceMeters != null)
          'near_distance_meters': nearDistanceMeters,
        if (trackingEnabled != null) 'tracking_enabled': trackingEnabled,
        if (trackingStartHour != null)
          'tracking_start_hour': trackingStartHour,
        if (trackingEndHour != null) 'tracking_end_hour': trackingEndHour,
        if (locationRetentionDays != null)
          'location_retention_days': locationRetentionDays,
        if (offlineAfterMinutes != null)
          'offline_after_minutes': offlineAfterMinutes,
      },
      fromData: (json) =>
          CompanySettings.fromJson(json as Map<String, dynamic>),
    );
    return envelope.data!;
  }
}
