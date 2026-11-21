// SPDX-License-Identifier: MIT

import './styles.scss';

import React, {
    useCallback, useEffect, useRef, useState,
} from 'react';
import { useParams } from 'react-router';
import { Row, Col } from 'antd/lib/grid';
import Title from 'antd/lib/typography/Title';
import Text from 'antd/lib/typography/Text';
import Button from 'antd/lib/button';
import Empty from 'antd/lib/empty';
import Result from 'antd/lib/result';

import { getCore } from 'cvat-core-wrapper';
import GoBackButton from 'components/common/go-back-button';
import CVATLoadingSpinner from 'components/common/loading-spinner';
import LabelCountsChart from './label-counts-chart';

const core = getCore();

export interface LabelCount {
    id: number;
    name: string;
    color: string;
    count: number;
}

interface AnnotationCounts {
    task_id: number;
    job_id: number | null;
    total: number;
    labels: LabelCount[];
}

async function fetchAnnotationCounts(taskId: number): Promise<AnnotationCounts> {
    const response = await core.server.request(
        `${core.config.backendAPI}/annotation-counts/${taskId}`,
        { method: 'GET' },
    ) as { data: AnnotationCounts };
    return response.data;
}

function AnnotationCountsPage(): JSX.Element {
    const { tid } = useParams<{ tid: string }>();
    const taskId = +tid;

    const [counts, setCounts] = useState<AnnotationCounts | null>(null);
    const [error, setError] = useState<Error | null>(null);
    const [fetching, setFetching] = useState(true);
    // only the newest request may update the page, a slow older one is ignored
    const latestRequest = useRef(0);

    const load = useCallback(async (): Promise<void> => {
        const request = ++latestRequest.current;
        setFetching(true);
        setError(null);
        try {
            const result = await fetchAnnotationCounts(taskId);
            if (request === latestRequest.current) setCounts(result);
        } catch (e) {
            if (request === latestRequest.current) setError(e as Error);
        } finally {
            if (request === latestRequest.current) setFetching(false);
        }
    }, [taskId]);

    useEffect(() => {
        load();
    }, [load]);

    let content: JSX.Element;
    if (error) {
        content = (
            <Result
                status='error'
                title='Could not load annotation counts'
                subTitle={error.message}
                extra={<Button type='primary' onClick={load}>Retry</Button>}
            />
        );
    } else if (fetching && !counts) {
        content = <CVATLoadingSpinner />;
    } else if (!counts || counts.total === 0) {
        content = <Empty description='This task has no annotations yet' />;
    } else {
        const unused = counts.labels.filter((label) => label.count === 0);
        content = (
            <>
                <Text className='cvat-annotation-counts-summary'>
                    {`${counts.total.toLocaleString()} annotations across `}
                    {`${counts.labels.length - unused.length} of ${counts.labels.length} labels`}
                </Text>
                <LabelCountsChart labels={counts.labels.filter((label) => label.count > 0)} />
                {unused.length > 0 && (
                    <Text type='secondary'>
                        {`No annotations yet: ${unused.map((label) => label.name).join(', ')}`}
                    </Text>
                )}
            </>
        );
    }

    return (
        <div className='cvat-annotation-counts-page'>
            <Row justify='center'>
                <Col span={22} xl={18} xxl={14}>
                    <GoBackButton />
                    <Title level={4}>{`Annotation counts for task #${taskId}`}</Title>
                    {content}
                </Col>
            </Row>
        </div>
    );
}

export default React.memo(AnnotationCountsPage);
