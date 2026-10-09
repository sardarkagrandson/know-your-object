// Mirrors backend/app/schemas/target.py and backend/app/services/surveys.py

export interface Coordinates {
  ra_deg: number;
  dec_deg: number;
  ra_hms: string;
  dec_dms: string;
  gal_l_deg: number | null;
  gal_b_deg: number | null;
  source: string | null;
}

export interface Kinematics {
  redshift: number | null;
  redshift_err: number | null;
  velocity_kms: number | null;
  velocity_err_kms: number | null;
  measurement_type: string | null;
  source: string | null;
}

export interface Morphology {
  type: string | null;
  quality: string | null;
  object_type: string | null;
  object_type_label: string | null;
  major_axis_arcmin: number | null;
  minor_axis_arcmin: number | null;
  position_angle_deg: number | null;
  source: string | null;
}

export interface Distance {
  value: number;
  unit: string;
  method: string | null;
  bibcode: string | null;
  source: string;
}

export interface GroupMembership {
  name: string;
  catalog: string | null;
  relation: "member" | "nearby";
  object_type: string | null;
  separation_arcmin: number | null;
  redshift: number | null;
}

export interface Environment {
  memberships: GroupMembership[];
  nearby_groups: GroupMembership[];
  search_radius_arcmin: number | null;
  note: string | null;
}

export interface ResolvedTarget {
  query: string;
  input_kind: "name" | "coordinates";
  main_id: string | null;
  ned_name: string | null;
  aliases: string[];
  coordinates: Coordinates;
  kinematics: Kinematics;
  morphology: Morphology;
  distances: Distance[];
  environment: Environment;
  suggested_fov_deg: number;
  sources: string[];
  warnings: string[];
  cached: boolean;
}

export interface Survey {
  id: string;
  label: string;
  band: string;
  description: string;
  cmap: string | null;
}

export interface Overlay {
  id: string;
  label: string;
  moc_url: string;
  color: string;
  description: string;
}

export interface SurveyCatalog {
  surveys: Survey[];
  overlays: Overlay[];
  default_grid: string[];
}
