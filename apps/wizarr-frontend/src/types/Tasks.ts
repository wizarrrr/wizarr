export interface Job {
    id: string;
    name: string;
    func: string;
    args: any[];
    kwargs: Object;
    trigger: string;
    start_date: string;
    minutes?: number;
    misfire_grace_time: number;
    max_instances: number;
    next_run_time: string;
    hours?: number;
}

export type JobList = Job[];
